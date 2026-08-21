from odoo import api, fields, models


class ProcurementPlan(models.Model):
    _inherit = 'procurement.plan'

    job_costing_id = fields.Many2one(
        'job.costing', string='Job Costing',
        compute='_compute_job_costing_id', store=True, index=True,
        help='Resolved from the related MRP production or purchase requisition.')
    project_id = fields.Many2one(
        'project.project', string='Project',
        related='job_costing_id.project_id', store=True, index=True)
    analytic_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account',
        related='job_costing_id.analytic_id', store=True)

    po_created_qty = fields.Float(
        string='PO Created', compute='_compute_tracking_qty', store=True,
        digits='Product Unit of Measure',
        help='Total quantity on non-cancelled purchase order lines (RFQ + PO).')
    grn_done_qty = fields.Float(
        string='GRN Done', compute='_compute_tracking_qty', store=True,
        digits='Product Unit of Measure',
        help='Total quantity received against purchase order lines.')
    balance_qty = fields.Float(
        string='Balance Qty', compute='_compute_tracking_qty', store=True,
        digits='Product Unit of Measure',
        help='Required qty minus GRN done qty, floored at zero.')

    @api.depends('mrp_id', 'mrp_id.job_cost_id',
                 'requisition_id', 'requisition_id.job_costing_id')
    def _compute_job_costing_id(self):
        for rec in self:
            jc = rec.mrp_id.job_cost_id if rec.mrp_id else False
            if not jc and rec.requisition_id:
                jc = rec.requisition_id.job_costing_id
            rec.job_costing_id = jc or False

    @api.depends('purchase_order_line_ids',
                 'purchase_order_line_ids.product_qty',
                 'purchase_order_line_ids.qty_received',
                 'purchase_order_line_ids.order_id.state',
                 'required_qty')
    def _compute_tracking_qty(self):
        for rec in self:
            active_lines = rec.purchase_order_line_ids.filtered(
                lambda l: l.order_id.state != 'cancel')
            po_created = sum(active_lines.mapped('product_qty')) or 0.0
            grn_done = sum(active_lines.mapped('qty_received')) or 0.0
            rec.po_created_qty = po_created
            rec.grn_done_qty = grn_done
            rec.balance_qty = max((rec.required_qty or 0.0) - grn_done, 0.0)
