from odoo import models, fields, api, _


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    epf_20 = fields.Boolean(string="EPF 20%")
    epf_12 = fields.Boolean(string="EPF 12%")
    epf_8 = fields.Boolean(string="EPF 8%")
    etf_3 = fields.Boolean(string="ETF 3%")
