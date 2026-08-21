from odoo import models, fields, _
from datetime import datetime
from odoo.http import request
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    gp_margin = fields.Boolean(string="Triggered GP Validation", default=False, copy=False)
    credit_limit = fields.Boolean(string="Triggered GP Validation", default=False, copy=False)
    payment_term = fields.Boolean(string="Triggered GP Validation", default=False, copy=False)
    triggered_gp_margin_validation = fields.Boolean(string="Triggered GP Validation", default=False, copy=False)
    triggered_gp_margin_validation1 = fields.Boolean(string="Triggered GP Validation ", default=False, copy=False)
    triggered_credit_limit_validation = fields.Boolean(string="Triggered Credit Limit Validation", default=False,
                                                       copy=False)
    triggered_credit_limit_validation1 = fields.Boolean(string="Triggered Credit Limit Validation ", default=False,
                                                        copy=False)
    triggered_payment_term_validation = fields.Boolean(string="Triggered Payment Term Validation", default=False,
                                                       copy=False)
    triggered_payment_term_validation1 = fields.Boolean(string="Triggered Payment Term Validation ", default=False,
                                                        copy=False)
    sale_order_approval_line_ids = fields.One2many('sale.order.approval.lines', 'sale_order_id')
    hide_approve_reject_button = fields.Boolean(string="Hide Approve Button",
                                                compute='_compute_hide_approve_reject_button')
    state = fields.Selection(selection_add=[('to approve', 'To Approve'), ('sale',)])

    def _compute_hide_approve_reject_button(self):
        """function to decide whether to hide approve & reject buttons"""
        for record in self:
            if record.sale_order_approval_line_ids.filtered(
                    lambda x: x.user_id.id == self._uid and x.state == 'requested'):
                record.hide_approve_reject_button = False
            else:
                record.hide_approve_reject_button = True

    def update_approvers(self):
        """function to update approvers"""
        vals = []
        count = 1
        for line in self.sale_order_approval_line_ids.filtered(lambda x: x.state not in ['approved', 'rejected']):
            vals.append((0, 0, {
                'sequence': count,
                'user_id': line.user_id.id,
                'so_approve_line_id': line.id,
            }))
            count += 1
        return {
            'name': _('Update Approvers'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.order.approvers.wizard',
            'target': 'new',
            'context': {
                'default_sale_order_approver_line_ids': vals,
                'default_type': 'update',
                'default_gp_margin': self.gp_margin,
                'default_credit_limit': self.credit_limit,
                'default_payment_term': self.payment_term
            }
        }

    def check_gp_margin(self):
        """Check gross profit margin"""
        gp_margin = False
        if self.company_id.gp_margin_validation == True:
            if self.triggered_gp_margin_validation == False:
                if self.company_id.gp_margin_company > 0.0:
                    if self.order_line:
                        for line in self.order_line:
                            if self.company_id.gp_margin_company > line.margin_percent * 100:
                                if request.params.get('model'):
                                    gp_margin = True
                else:

                    if self.order_line:
                        for line in self.order_line:
                            if line.product_id.categ_id.gp_margin > line.margin_percent * 100:
                                if request.params.get('model'):
                                    gp_margin = True
        return gp_margin

    def check_credit_limit(self):
        """Check credit limit"""
        credit_limit = False
        if self.company_id.credit_limit_validation == True:
            if self.triggered_credit_limit_validation == False:
                if self.partner_id.remaining_credit_limit < self.amount_total and self.partner_id.have_credit_limit:
                    if request.params.get('model'):
                        credit_limit = True
        return credit_limit

    def check_payment_term(self):
        """Check payment terms validations"""
        payment_term = False
        if self.company_id.payment_terms_validation == True:
            if self.triggered_payment_term_validation == False:
                invoices = self.env['account.move'].search(
                    [('state', '=', 'posted'),
                     ('partner_id', '=', self.partner_id.id),
                     ('invoice_date_due', '<', datetime.today().date()),
                     ('payment_state', '!=', 'paid'),
                     ('move_type', '=', 'out_invoice')])
                if invoices:
                    if request.params.get('model'):
                        payment_term = True
        return payment_term

    def send_for_approval(self):
        """
        send_for_approval()

        Sends the current sale order for approval, calculating additional conditions and
        determining which users should approve it. Validates multiple criteria like job
        costing state, gross profit margin, credit limit, and payment terms. It will also
        assign approvers based on predefined approval lines.

        Raises:
            UserError: If the associated job costing sheet is not in the 'done' state.
            UserError: If the sale order value does not fall within any defined approval
                       lines.

        Parameters:
            None

        Returns:
            dict: Action containing the form view of the `sale.order.approvers.wizard`
            model, pre-filled with context parameters necessary for approvers to review
            the sale order.
        """
        if self.job_costing_id:
            if self.job_costing_id.state != 'done' and self.doc_type == 'sale':
                raise UserError(_('Job Costing Sheet should need to be in Done stage'))
        gp_margin = self.check_gp_margin()
        credit_limit = self.check_credit_limit()
        payment_term = self.check_payment_term()
        self.write({
            'gp_margin': gp_margin,
            'credit_limit': credit_limit,
            'payment_term': payment_term,
        })
        amount = self.currency_id._convert(self.amount_total, self.currency_id, self.company_id,
                                           self.date_order or fields.Date.today())
        approval_line = self.company_id.sale_order_config_approval_line_ids.filtered(
            lambda x: x.amount_from <= amount <= x.amount_to)
        if not approval_line:
            raise UserError("Please define an approval line for the sale order value.")
        vals = []
        count = 1
        all_users = approval_line.user_ids
        if gp_margin:
            all_users |= self.env.ref('centrics_sale_multi_user_approval.group_show_margin_sale_multi_user').users
        if credit_limit:
            all_users |= self.env.ref('centrics_sale_multi_user_approval.group_show_credit_limit_and_payment_terms_sale_multi_user').users
        if payment_term:
            all_users |= self.env.ref('centrics_sale_multi_user_approval.group_show_credit_limit_and_payment_terms_sale_multi_user').users
        for user in all_users:
            vals.append((0, 0, {
                'sequence': count,
                'user_id': user.id,
            }))
            count += 1

        amount_total = self.amount_total
        total_quotation_amount = round(self.total_quotation_amount, 3)
        if self.doc_type == 'quotation':
            if total_quotation_amount != amount_total:
                raise UserError("Total Quotation Amount should be equal to Total Amount")

        return {
            'name': _('Send For Approval'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.order.approvers.wizard',
            'target': 'new',
            'context': {'default_sale_order_approver_line_ids': vals,
                        'default_gp_margin': gp_margin,
                        'default_credit_limit': credit_limit,
                        'default_payment_term': payment_term}
        }

    def send_to_next_approver(self):
        """This function automatically sets next available approver."""
        if self.state in ['draft', 'sent']:
            self.write({
                'state': 'to approve'
            })
        next_approvers = self.sale_order_approval_line_ids.filtered(lambda x: x.state == 'pending')
        if next_approvers:
            next_approvers[0].write({
                'state': 'requested',
                'approval_request_datetime': datetime.now(),
            })
            template_id = self.env.ref('centrics_sale_multi_user_approval.centrics_sale_multi_user_approval_request_for_approval_mail_template')
            msg = 'There is a pending sale order for your approval.'
            self.with_context(mail_body={}).send_email_sale(self.id, self._context.get('active_model'), "Request for Approval", next_approvers[0].user_id, template_id, msg)

    def button_reject(self):
        """New function to reject POs."""
        approver_line = self.sale_order_approval_line_ids.filtered(
            lambda x: x.user_id.id == self._uid and x.state == 'requested')
        if not approver_line:
            raise UserError("You Don't have access to approve.")
        approver_line.write({
            'state': 'rejected',
            'status_updated_datetime': datetime.now(),
        })
        self.action_cancel()
        template_id = self.env.ref(
            'centrics_sale_multi_user_approval.centrics_sale_multi_user_approval_reject_or_approve_template')
        msg = 'The following sale order is rejected by %s' % self.env['res.users'].browse(self._uid).name
        self.with_context(mail_body={}).send_email_sale(self.id, self._context.get('active_model'),
                                                            "Rejected", self.create_uid, template_id, msg)

    def button_approve(self):
        """This is a core function which is completely overidden"""
        approver_line = self.sale_order_approval_line_ids.filtered(
            lambda x: x.user_id.id == self._uid and x.state == 'requested')
        if not approver_line:
            raise UserError("You Don't have access to approve.")
        approver_line.write({
            'state': 'approved',
            'status_updated_datetime': datetime.now(),
        })
        next_approver_line = self.sale_order_approval_line_ids.filtered(lambda x: x.state == 'pending')
        if next_approver_line:
            self.send_to_next_approver()
        else:
            template_id = self.env.ref(
                'centrics_sale_multi_user_approval.centrics_sale_multi_user_approval_reject_or_approve_template')
            msg = 'The following sale order is approved by %s' % self.env['res.users'].browse(
                self._uid).name
            self.with_context(mail_body={}).send_email_sale(self.id, self._context.get('active_model'),
                                                                "Approved", self.create_uid, template_id, msg)
            self.button_confirm()

    def button_confirm(self):
        """Inheriting confirm button inorder to add to confirm to approve state SOs."""
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.state not in ['draft', 'sent', 'to approve']:
                continue
            order._add_supplier_to_product()
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
            self.write({'state': 'sale', 'date_approve': fields.Datetime.now()})
            self.filtered(lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
        return res

    def send_email_sale(self, record, model, subject, users, template_id, msg):
        """Common function to send email. Parameters contains all required date for the mail template"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = '%s/web?login/#id=%s&view_type=form&model=%s' % (base_url, record, model)
        context = self.env.context.get('mail_body')
        context['mail_to'] = ','.join([str(x.partner_id.id) for x in users])
        context['custom_url'] = url
        context['subject'] = subject
        context['msg_type'] = msg
        context['credit_limit'] = self.credit_limit
        context['gp_margin'] = self.gp_margin
        context['payment_term'] = self.payment_term
        self.env['mail.template'].sudo().browse(template_id.id).with_context(context).send_mail(self.id, True)


class SaleOrderApprovalLines(models.Model):
    _name = 'sale.order.approval.lines'
    _description = "Sale Order Approval Lines"
    _order = 'sequence'

    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    sequence = fields.Integer(string="Sequence", default=1)
    user_id = fields.Many2one('res.users', string="Users")
    state = fields.Selection([('pending', 'Pending'), ('requested', 'Requested'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')
    approval_request_datetime = fields.Datetime(string="Approval Request Date")
    status_updated_datetime = fields.Datetime(string="Last Status Updated Date")
    show_signature = fields.Boolean(string="Show Signature")
