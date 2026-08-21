from datetime import datetime, timedelta
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    is_pyaroll_integration_enabled = fields.Boolean(related='company_id.is_enable_payroll_integration', store=True)

    # @api.depends('employee_id', 'date_from', 'date_to')
    # def _compute_input_line_ids(self):
    #     """Overiding onchange function in core"""
    #     # Check Loan module settings to check the enabling of payroll integration with loans
    #     if not self.env.company.is_enable_payroll_integration:
    #         return super(HrPayslip, self)._compute_input_line_ids()
    #
    #     return_obj = super(HrPayslip, self)._compute_input_line_ids()
    #     for payslip in self:
    #         if payslip.employee_id and payslip.date_from and payslip.date_to:
    #             payslip.input_line_ids = [(6, 0, [])]
    #             year = payslip.date_from.year
    #             month = payslip.date_from.month
    #             loan_installment_line_ids = self.env['employee.loan.installment.line'].search([('employee_id', '=', payslip.employee_id.id), ('year', '<=', year), ('month', '<', month),('')])
    #             for loan_installment in loan_installment_line_ids:
    #                 line.input_line_ids.append((0, 0, {}))