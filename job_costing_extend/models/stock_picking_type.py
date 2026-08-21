from odoo import fields, models, api, _


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    default_mr_picking = fields.Boolean(string='Default MR Picking', default=False)