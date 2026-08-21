from odoo import models,fields,api,_


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    registration_number = fields.Char(string="Registration Number", compute="_compute_registration_number", store=True)


    @api.depends('employee_number')
    def _compute_registration_number(self):
        for record in self:
            if record.employee_number:
                record.registration_number = record.employee_number