from odoo import models,fields,api,_


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    educational_qualification_line_ids =  fields.One2many('educational.qualification.line', 'employee_id')