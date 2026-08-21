# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.exceptions import UserError


class MakeEmployeeOvertime(models.TransientModel):
    _name = "make.employee.overtime"
    _description = "Make Employee Overtime"

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    is_all_employees = fields.Boolean(string="All Employees")
    employee_id = fields.Many2one('hr.employee', string="Employee",
                                  domain="[('contract_id.is_eligible_for_overtime', '=', True)]")
    department_id = fields.Many2one('hr.department', string="Department")

    def print_employee_overtime(self):
        """
         Print Employee Overtime Report for selected dates.
        """
        if not self.is_all_employees and not self.employee_id:
            raise UserError("Please select an employee or all employees.")

        domain = ['|', '|', ('normal_overtime', '>', 0.0), ('double_overtime', '>', 0.0), ('triple_overtime', '>', 0.0)]

        if self.is_all_employees:
            domain.append(('eligible_for_overtime', '=', True))
            if self.department_id:
                domain.append(('department_id', '=', self.department_id.id))
        elif self.employee_id:
            domain.append(('employee_id', '=', self.employee_id.id))
            self.department_id = False

        if self.start_date:
            domain.append(('check_in', '>=', self.start_date))
        if self.end_date:
            domain.append(('check_in', '<=', self.end_date))

        attendance_records = self.env['hr.attendance'].search_read(domain,
            fields=['employee_id', 'check_in', 'check_out', 'normal_overtime', 'double_overtime', 'triple_overtime'])

        if not attendance_records:
            raise UserError("No attendance records found for selected dates.")
        data = {'form': self.read()[0],
                'attendance_records': attendance_records,
        }
        return self.env.ref('centrics_hr_overtime.action_report_employee_overtime').report_action(self, data=data)





