from odoo import api, fields, models


class MaterialPurchaseRequisitionLine(models.Model):
    _inherit = 'material.purchase.requisition.line'

    from_location_id = fields.Many2one(
        'stock.location', string='From Location',
        compute='_compute_from_location',
        store=True, readonly=True,
        help='Source location for this line, inherited from the requisition '
             'header. Used to compute location-specific On-Hand and Forecasted '
             'quantities.')

    on_hand_at_location = fields.Float(
        string='On-Hand (Location)',
        compute='_compute_location_stock',
        digits='Product Unit of Measure',
        help='Unreserved on-hand quantity of the product at the From Location.')
    forecasted_at_location = fields.Float(
        string='Forecasted (Location)',
        compute='_compute_location_stock',
        digits='Product Unit of Measure',
        help='Forecasted quantity at the From Location '
             '(Available - Reserved + Incoming - Outgoing).')

    @api.depends('requisition_id.header_location_id',
                 'requisition_id.custom_picking_type_id')
    def _compute_from_location(self):
        for rec in self:
            header_loc = rec.requisition_id.header_location_id
            if header_loc:
                rec.from_location_id = header_loc
            else:
                rec.from_location_id = (
                    rec.requisition_id.custom_picking_type_id
                       .default_location_src_id or False)

    @api.depends('product_id', 'from_location_id')
    def _compute_location_stock(self):
        for rec in self:
            if not rec.product_id or not rec.from_location_id:
                rec.on_hand_at_location = 0.0
                rec.forecasted_at_location = 0.0
                continue
            product = rec.product_id.with_context(
                location=rec.from_location_id.id,
                company_id=rec.requisition_id.company_id.id,
            )
            rec.on_hand_at_location = product.qty_available
            rec.forecasted_at_location = product.virtual_available
