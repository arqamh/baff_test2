# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        """
        @override - adding analytic distribution to the stock picking
        """
        res = super()._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        res.update({
            'analytic_distribution': self.analytic_distribution
        })
        return res
