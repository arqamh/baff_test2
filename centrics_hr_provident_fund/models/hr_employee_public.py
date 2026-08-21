from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    is_provident_fund_eligible = fields.Boolean(string="Eligible for EPF?")
    epf_number = fields.Char(string="EPF  Number")
    date_of_epf_resisted = fields.Date(string="Date of EPF Resisted")
