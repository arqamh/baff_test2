from odoo import models,fields,api,_


class BufferTimeConfiguration(models.Model):
    _inherit = 'buffer.time.configuration'

    employee_type = fields.Selection(
        selection=lambda self: self.env['hr.employee'].fields_get(['ocean_voyager_emp_category'])['ocean_voyager_emp_category']['selection'],
        string="Employee Type",
        help="Values for employee type fetched from the ocean_voyager_emp_category field in hr.employee"
    )