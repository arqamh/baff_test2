from odoo import models,fields,api,_
from odoo.exceptions import UserError,ValidationError


class EmployeeLoanGuarantor(models.Model):
    _name = 'employee.loan.guarantor'
    _description = 'Employee Loan Guarantor'

    employee_loan_id = fields.Many2one('employee.loan',string="Employee Loan")
    employee_id = fields.Many2one('hr.employee',string="Employee")
    job_id = fields.Many2one('hr.job',string="Job", related='employee_id.job_id',readonly=True)
    department_id = fields.Many2one('hr.department',string="Department", related='employee_id.department_id',readonly=True)


