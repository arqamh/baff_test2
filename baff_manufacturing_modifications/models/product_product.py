from odoo import models
from odoo.tools import float_round, groupby


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    def _set_price_from_bom(self, boms_to_recompute=False):
        """ Overriding core method to exclude the operations cost from the product cost """
        self.ensure_one()
        bom = self.env['mrp.bom']._bom_find(self)[self]
        if bom:
            self.standard_price = self._compute_bom_price_without_operations(bom, boms_to_recompute=boms_to_recompute)
        else:
            bom = self.env['mrp.bom'].search([('byproduct_ids.product_id', '=', self.id)], order='sequence, product_id, id', limit=1)
            if bom:
                price = self._compute_bom_price_without_operations(bom, boms_to_recompute=boms_to_recompute, byproduct_bom=True)
                if price:
                    self.standard_price = price

    def _compute_bom_price_without_operations(self, bom, boms_to_recompute=False, byproduct_bom=False):
        """ Method to calculate product cost based on the BOM excluding operation cost. """
        self.ensure_one()
        if not bom:
            return 0
        if not boms_to_recompute:
            boms_to_recompute = []
        total = 0

        for line in bom.bom_line_ids:
            if line._skip_bom_line(self):
                continue

            # Compute recursive if line has `child_line_ids`
            if line.child_bom_id and line.child_bom_id in boms_to_recompute:
                child_total = line.product_id._compute_bom_price(line.child_bom_id, boms_to_recompute=boms_to_recompute)
                total += line.product_id.uom_id._compute_price(child_total, line.product_uom_id) * line.product_qty
            else:
                total += line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id) * line.product_qty
        if byproduct_bom:
            byproduct_lines = bom.byproduct_ids.filtered(lambda b: b.product_id == self and b.cost_share != 0)
            product_uom_qty = 0
            for line in byproduct_lines:
                product_uom_qty += line.product_uom_id._compute_quantity(line.product_qty, self.uom_id, round=False)
            byproduct_cost_share = sum(byproduct_lines.mapped('cost_share'))
            if byproduct_cost_share and product_uom_qty:
                return total * byproduct_cost_share / 100 / product_uom_qty
        else:
            byproduct_cost_share = sum(bom.byproduct_ids.mapped('cost_share'))
            if byproduct_cost_share:
                total *= float_round(1 - byproduct_cost_share / 100, precision_rounding=0.0001)
            return bom.product_uom_id._compute_price(total / bom.product_qty, self.uom_id)