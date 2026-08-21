from odoo import fields, api, models


class InheritAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    hs_code = fields.Char(string="HS Code")