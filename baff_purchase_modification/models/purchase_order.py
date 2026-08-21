from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'


    shipment_details_ids = fields.One2many('purchase.shipment.details', 'purchase_id')
    

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    requested_user = fields.Many2one('res.users')
    last_purchase_price = fields.Float(compute="compute_last_purchase_price")

    def compute_last_purchase_price(self):
        """Get last purchase price"""
        for record in self:
            last_order_line = self.env['purchase.order.line'].search([('id', '!=', record.id),('product_id', '=', record.product_id.id), ('state', '=', 'purchase')], order='name desc', limit=1)
            if last_order_line:
                record.last_purchase_price = last_order_line.price_unit
            else:
                record.last_purchase_price = 0.00