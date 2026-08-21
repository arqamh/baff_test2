from odoo import models, fields, api


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    def _get_employee_fields_for_tablet(self):
        """
        Extra additional details to the employee details
        """
        data = super()._get_employee_fields_for_tablet()
        data.append('job_title')
        return data