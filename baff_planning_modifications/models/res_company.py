from odoo import fields, models, api, _


class Company(models.Model):
    _inherit = 'res.company'

    holiday_ot = fields.Float(string="Holiday OT")
    saturday_ot = fields.Float(string="Saturday OT")
    working_days_ot = fields.Float(string="Working Days OT")
