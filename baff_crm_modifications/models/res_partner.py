from odoo import api, fields, models, _


class InheritResPartner(models.Model):
    _inherit = 'res.partner'

    partner_code = fields.Char(string="Code")
