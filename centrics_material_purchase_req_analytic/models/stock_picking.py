# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = [
        'analytic.mixin',
        'stock.picking'
    ]


