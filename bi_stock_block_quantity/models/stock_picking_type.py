# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'
    _description = ' Allow stock picking on Exceeded Quantity'

    exceeded_quantity = fields.Boolean(string=" Allow stock picking on Exceeded Quantity")

