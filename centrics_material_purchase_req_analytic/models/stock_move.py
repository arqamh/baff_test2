# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockMove(models.Model):
    _name = 'stock.move'
    _inherit = [
        'analytic.mixin',
        'stock.move'
    ]


