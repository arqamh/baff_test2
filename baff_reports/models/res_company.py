from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    second_logo_for_invoice = fields.Binary(string='Second Logo for Invoice')