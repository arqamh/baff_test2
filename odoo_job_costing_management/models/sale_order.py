from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    hide_job_cost_create = fields.Boolean(string="Hide Job Cost Create", compute='_compute_hide_job_cost_create')
    job_costing_id = fields.Many2one('job.costing', string="Job Costing Sheet")
    job_costing_required = fields.Boolean(string="Job Costing Required", default=True)

    def search_revised_job_costing_sheets(self):
        """Search and filter revised job costing sheets related to this quotation."""
        return self.env['job.costing'].search([('quotation_id', '=', self.id), ('original_job_costing_id', '!=', False)])

    def _compute_hide_job_cost_create(self):
        for record in self:
            record.hide_job_cost_create = True if record.job_costing_id else False

    def create_job_costing_sheet(self):
        # Build a finished-good line for every product-typed SO line. Sub-/
        # consu-/ service-type lines are skipped — they should be handled as
        # Labor / Overhead invoiceable lines, not as finished goods.
        product_lines = self.order_line.filtered(
            lambda l: l.product_id and l.product_id.type in ('product', 'consu'))
        finished_good_cmds = [(0, 0, {
            'product_id': line.product_id.id,
            'product_qty': line.product_uom_qty,
            'sale_order_line_id': line.id,
            'sequence': line.sequence,
        }) for line in product_lines]

        job_costing_sheet = self.env['job.costing'].create({
            "partner_id": self.partner_id.id,
            "quotation_id": self.id,
            "po_number": self.client_order_ref,
            "lead_id": self.opportunity_id.id,
            "sales_person_id": self.user_id.id,
            "user_id": self.env.user.id,
            "customer_currency_id": self.currency_id.id,
            "currency_id": self.env.company.currency_id.id,
            "finished_good_ids": finished_good_cmds,
            "boat_type_id": self.boat_type_id.id, # get this into the baff sales modifications modules
            "analytic_plan_id": self.analytic_plan_id.id,
            "project_start_date": self.project_start_date
        })
        self.job_costing_id = job_costing_sheet.id
        components = []
        if self.boat_type_id:
            boat = self.env['mrp.bom'].search([
                ('boat_type_ids', 'in', self.boat_type_id.id),
                ('bom_type', '=', 'base_bom'),
                ('is_this_standard_bom', '=', True),
            ], limit=1)
            if boat:
                components += boat[0]
        if self.options:
            components += self.options
        if components:
            total_qty = sum(product_lines.mapped('product_uom_qty')) if product_lines else 1
            self.job_costing_id.action_add_component(components, quantity=total_qty)
        return {
            'name': _(job_costing_sheet.number),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'job.costing',
            'target': 'current',
            'res_id': job_costing_sheet.id,
        }

    def action_open_job_costing(self):
        """open job costing sheet of the current sales order"""
        if self.job_costing_id:
            action = {
                'name': 'Job',
                'type': 'ir.actions.act_window',
                'res_model': 'job.costing',
                'res_id': self.job_costing_id.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current'
            }
            return action

    def action_open_revised_job_costing(self):
        """Open job costing sheet showing only revised copies related to the quotation."""
        self.ensure_one()
        revised_job_costing_sheets = self.search_revised_job_costing_sheets()
        if revised_job_costing_sheets:
            action = {
                'name': 'Revised Job Costing',
                'type': 'ir.actions.act_window',
                'res_model': 'job.costing',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', revised_job_costing_sheets.ids)],
                'target': 'current'
            }
            return action
        else:
            raise UserError(_('No revised job costing sheets found for this quotation.'))

    def update_sales_price(self):
        """update sales price"""
        if not self.job_costing_id:
            raise UserError("Please create a job Costing sheet.")
        elif self.doc_type == "quotation":
            if self.job_costing_id.filtered(lambda x: x.state != 'approved'):
                raise ValidationError("Please make sure the job costing sheets are approved.")
            else:
                for line in self.order_line:
                    line.write({
                        "price_unit": self.job_costing_id.jobcost_total / line.product_uom_qty
                    })

    def action_draft(self):
        """Override core method for automate the revised job costing sheet"""
        orders = self.filtered(lambda s: s.state in ['cancel', 'sent'])
        orders.write({
            'state': 'draft',
            'signature': False,
            'signed_by': False,
            'signed_on': False,
        })
        # Automatically call action_revise_job_costing for related job costing sheets
        for order in orders:
            job_costing = self.env['job.costing'].search([('quotation_id', '=', order.id), ('original_job_costing_id', '=', False)])
            job_costing.action_revise_job_costing()
        return True
