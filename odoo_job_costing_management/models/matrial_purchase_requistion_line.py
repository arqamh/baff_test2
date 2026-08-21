from odoo import models, fields, api
from . import job_costing


class MaterialPurchaseRequisitionLine(models.Model):
    _inherit = "material.purchase.requisition.line"

    job_costing_id = fields.Many2one('job.costing', string='Job Costing')
    job_cost_line_id = fields.Many2one('job.cost.line', string='Job Cost Line')
    job_prepared_by = fields.Many2one(related="job_cost_line_id.prepared_by")
    analytic_plan_id = fields.Many2one('account.analytic.plan', string="Cost Center", related="job_costing_id.analytic_plan_id")
    show_job_costing = fields.Boolean(string="Show Job Costing Sheet", compute='_compute_show_job_costing')
    scheduled_date = fields.Date(string="Scheduled Date")
    required_quantity = fields.Float(string="Required Quantity")
    parent_bom_id = fields.Many2one('mrp.bom', string="Parent BOM")
    parent_bom_name = fields.Char(string="Parent BOM")
    component = fields.Char(related='job_cost_line_id.component', string="Component")

    def _compute_show_job_costing(self):
        for record in self:
            show_job_costing = True
            if record.requisition_id:
                if record.requisition_id.requisition_line_ids:
                    source = record.requisition_id.requisition_line_ids.mapped('job_costing_id')
                    if source:
                        if len(source) == 1:
                            show_job_costing = False
            record.show_job_costing = show_job_costing

    @api.onchange('job_cost_line_id')
    def onchange_job_cost_line_id(self):
        """Update remaining qty when change job cost line"""
        if self.job_cost_line_id and self.remaining_qty == 0:
            self.remaining_qty = self.job_cost_line_id.remaining_qty
            self.product_id = self.job_cost_line_id.product_id.id
            self.description = self.job_cost_line_id.description
            self.uom = self.job_cost_line_id.uom_id.id