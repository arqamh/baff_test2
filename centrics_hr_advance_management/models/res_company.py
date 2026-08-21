from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    enable_advance_approval = fields.Boolean(
        string="Employee Advance Approval",)

    enable_payroll_integration = fields.Boolean(
        string="Payroll Integration")