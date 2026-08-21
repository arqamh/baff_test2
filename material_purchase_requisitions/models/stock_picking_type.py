# -*- coding: utf-8 -*-

from odoo import models, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    def name_get(self):
        """Override to display only the picking type name without company"""
        result = []
        for record in self:
            result.append((record.id, record.name))
        return result