import re

from odoo import api, fields, models, _, exceptions
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    customer_po_available = fields.Boolean(string="Customer PO Available")
    cash_project_confirmation = fields.Boolean(string="Cash Project Confirmation")
    confirmed_email_text = fields.Boolean(string="Confirmed Email/Text")
    quotation_required = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Quotation Required', default='no')
    customer_po_available = fields.Boolean(string="Customer PO Available")
    doc_type = fields.Selection([('quotation', 'Quotation'), ('sale', 'Sale')], string="Type", default='quotation',
                                copy=False)
    quotation_id = fields.Many2one('sale.order', string='Quotation', copy=False)
    sale_id = fields.Many2one('sale.order', string='Sale', copy=False)
    state = fields.Selection(selection_add=[
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('quotation_done', 'Quotation Confirmed'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft')
    so_created = fields.Boolean(string="SO Created", copy=False)
    state_quotation = fields.Selection(related="state", string='Status ')
    state_sale = fields.Selection(related="state", string='Status  ')
    invoiceable_line = fields.One2many('invoiceable.lines', 'order_id', string='Invoiceable Lines', copy=False)
    so_invoiceable_line = fields.One2many('invoiceable.lines', 'so_order_id', string='Invoiceable Lines ', copy=False)

    total_invoiceable_amount = fields.Float( string='Total Invoiceable Amount', compute='_compute_total_invoiceable_amount', strore=True, digits=(16, 3))
    total_quotation_amount = fields.Float( string='Total Quotation Amount', compute='_compute_total_quotation_amount', strore=True, digits=(16, 3))


    @api.depends('so_invoiceable_line.price_subtotal')
    def _compute_total_invoiceable_amount(self):
        for record in self:
            record.total_invoiceable_amount = sum(record.so_invoiceable_line.mapped('price_subtotal'))

    @api.depends('invoiceable_line.price_subtotal')
    def _compute_total_quotation_amount(self):
        for record in self:
            record.total_quotation_amount = sum(record.invoiceable_line.mapped('price_subtotal'))

    @api.model
    def create(self, vals):
        """Overriding create method to generate a new sequence number to Quotations"""
        if vals.get('name', _('New')) == _('New') and vals.get('doc_type') in ["quotation", None]:
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            vals['name'] = self.env['ir.sequence'].next_by_code('sale.quotation.code', sequence_date=seq_date) or _(
                'New')
        result = super(SaleOrder, self).create(vals)
        return result

    def write(self, vals):
        """Overdoing to avoid sale orders archiving"""
        for record in self:
            if vals.get('active') == False and record.doc_type == "quotation" and record.state == "quotation_done":
                raise UserError("You cannot archive Quotations in Quotation Confirmed State.")
        return super(SaleOrder, self).write(vals)

    def action_confirm(self):
        """If quotation it will move to quotation_done state, otherwise normal workflow"""
        if self.doc_type == "quotation":
            if self.job_costing_id.filtered(lambda x: x.state != 'approved'):
                raise ValidationError("Please make sure the job costing sheets are approved.")
            if self.quotation_required == 'no':
                if self.customer_po_available or self.cash_project_confirmation or self.confirmed_email_text:
                    pass
            self.write({"state": "quotation_done"})
            return self.action_create_so()

            # Send email to group based on quotation status
            group_id = self.env.ref('odoo_job_costing_management.group_job_costing_production')
            email_template = self.env.ref(
                'centrics_sales_separate_process.centrics_sales_separate_process_mail_template_quotation_confirm')
            users = group_id.users
            email_to = False
            for u in users:
                if u.email:

                    email_to = ', '.join([str(u.email)])
            email_from = self.env.user.email

            ctx = {
                'quotation_number': self.name,
                'quotation_status': self.state,
                'email_from': email_from,
                'email_to': email_to,
                'object': self,
                'user': self.env.user,
            }
            email_template.with_context(ctx).send_mail(self.id, force_send=True)
            self.write({"state": "quotation_done"})

        else:
            if self.job_costing_id:
                if self.job_costing_id.state != 'done':
                    raise ValidationError("Please make sure the job costing sheets are approved.")
            return super(SaleOrder, self).action_confirm()

    def action_create_so(self):
        """Create a separate sales order based on quotation and then view it"""
        default = {
            "doc_type": "sale",
            "quotation_id": self.id,
            "opportunity_id": self.opportunity_id.id,
        }
        new_sales_order = self.copy(default)
        project_name = re.sub('\D', '', str(self.opportunity_id.inquiry_number or new_sales_order.display_name))
        refactored_project_name = "P%s%s" % (str(project_name), str(self.analytic_plan_id.name))  # Need to add analytic plane code instead of name
        project = self.project_id
        if not project:
            project = self.env['project.project'].create({
                "name": self.job_costing_id.project_name,
                "partner_id": self.partner_id.id,
                "user_id": self.user_id.id,
                "privacy_visibility": "employees",
            })
            project = project
            new_sales_order.project_id = project.id
            new_sales_order.analytic_account_id = project.analytic_account_id.id
        self.job_costing_id.write({
            "state": "ready_for_production",
            "project_id": project.id,
            "sale_id": new_sales_order.id,
            "analytic_id": project.analytic_account_id.id,
        })
        project.analytic_account_id.write({
            "plan_id": self.analytic_plan_id.id
        })
        # if project:
            # if self.order_line:
            #     for order_line in self.order_line:
            #         order_line.product_id.write({
            #             'name': project.name
            #         })
            #         if self.opportunity_id.inquiry_number == order_line.name:
            #             order_line.name = project.name
        if self.invoiceable_line:
            for line in self.invoiceable_line:
                line.so_order_id = new_sales_order.id
        self.write({
            "so_created": True,
            "sale_id": new_sales_order.id
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": new_sales_order.id,
            "target": "current",
        }

    def action_view_so(self):
        """This function opens the sales orders"""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action["domain"] = [("id", "=", self.sale_id.id)]
        return action
