from bdb import effective
from datetime import datetime
from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero

import logging
_logger = logging.getLogger(__name__)

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    force_create_quant = fields.Boolean(string='Force Create Quant')

    def trigger_server_action(self):
        cutoff_date = "2025-03-31 23:59:59"
        current_date = datetime.now()
        product_ids = self.mapped('product_id').ids
        products = self.env['product.product'].browse(product_ids)

        move_lines = self.env['stock.move.line'].search([
            ('product_id', 'in', product_ids),
            ('date', '<=', cutoff_date),
        ])

        updated_move_lines = self.env['stock.move.line'].search([
            ('product_id', 'in', product_ids),
            ('date', '<=', current_date),
        ])

        internal_locations = self.env['stock.location'].search([('usage', '=', 'internal')])
        created_inventories = []

        for location in internal_locations:
            inventory_lines = []

            for product in products:
                # Filter moves for this product
                product_moves = move_lines.filtered(lambda m: m.product_id.id == product.id)

                final_product_moves = updated_move_lines.filtered(lambda m: m.product_id.id == product.id)
                in_location = product_moves.filtered(lambda m: m.location_dest_id.id == location.id)
                out_location = product_moves.filtered(lambda m: m.location_id.id == location.id)
                if in_location or out_location:
                    qty_in = sum(in_location.mapped('qty_done'))
                    qty_out = sum(out_location.mapped('qty_done'))
                    net_qty = qty_in - qty_out

                    final_qty_in = sum(final_product_moves.filtered(lambda m: m.location_dest_id.id == location.id).mapped('qty_done'))
                    final_qty_out = sum(final_product_moves.filtered(lambda m: m.location_id.id == location.id).mapped('qty_done'))
                    final_net_qty = final_qty_in - final_qty_out

                    effective_quantity = final_net_qty - net_qty

                    adjustment_id = self.env['stock.quant'].search([
                        ('location_id', '=', location.id),
                        ('product_id', '=', product.id),
                    ])
                    if adjustment_id:
                        adjustment_id.inventory_quantity = effective_quantity
                    else:
                        adjustment_id = self.env['stock.quant'].with_context(force_create_quant=True).sudo().create({
                            'location_id': location.id,
                            'product_id': product.id,
                            'product_uom_id': product.uom_id.id,
                            'inventory_quantity': effective_quantity,
                        })

                    adjustment_id.action_apply_inventory()
