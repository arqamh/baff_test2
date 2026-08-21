from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    registration_number = fields.Char(string="Registration Number")
