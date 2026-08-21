from odoo import models,fields,api,_


class ResCompany(models.Model):
    _inherit = 'res.company'

    employee_approval_needed = fields.Boolean(string="Employee Approval Needed")
    employee_number_auto_generate = fields.Boolean(string="Employee Number Auto Generate")
    retirement_age = fields.Integer(string="Retirement Age", default=60)
    enable_onboarding =  fields.Boolean(string="Enable Onboarding")