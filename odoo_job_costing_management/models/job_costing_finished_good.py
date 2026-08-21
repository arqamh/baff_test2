from odoo import api, fields, models


class JobCostingFinishedGood(models.Model):
    _name = 'job.costing.finished.good'
    _description = 'Job Costing Finished Good'
    _order = 'job_costing_id, sequence, id'

    job_costing_id = fields.Many2one(
        'job.costing', string='Job Costing Sheet',
        required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)

    product_id = fields.Many2one(
        'product.product', string='Finished Good', required=True)
    product_tmpl_id = fields.Many2one(
        related='product_id.product_tmpl_id', store=True)
    product_uom_id = fields.Many2one(
        'uom.uom', string='Unit of Measure',
        related='product_id.uom_id', readonly=False)

    product_qty = fields.Float(
        string='Quantity', default=1.0, digits='Product Unit of Measure')
    unit_price = fields.Float(
        string='Unit Price', digits='Product Price',
        help='Allocated unit price for this finished good — set when the '
             'job-costing sheet is approved.')
    subtotal_cost = fields.Float(
        string='Subtotal', compute='_compute_subtotal_cost', store=True)

    bom_id = fields.Many2one(
        'mrp.bom', string='BOM',
        help='BOM created for this finished good on production approval.')
    mrp_production_id = fields.Many2one(
        'mrp.production', string='Manufacturing Order',
        help='Manufacturing order created for this finished good.')

    sale_order_line_id = fields.Many2one(
        'sale.order.line', string='Quotation Line',
        help='Source sale order line on the quotation that this finished '
             'good was derived from.')

    @api.depends('product_qty', 'unit_price')
    def _compute_subtotal_cost(self):
        for rec in self:
            rec.subtotal_cost = rec.product_qty * rec.unit_price
