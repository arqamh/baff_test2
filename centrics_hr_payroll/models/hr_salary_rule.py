from odoo import models,fields,api, _


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    fixed_allowance_deduction_id = fields.Many2one(
        'fixed.allowance.deduction',
        string='Fixed Allowance/Deduction',
        help='Choose a Fixed Allowance or Deduction for the Salary Rule'
    )

    appear_as_subtotal_in_payslip = fields.Boolean(string="Appear as Subtotal in Payslip")
    appear_on_detail_payroll_report = fields.Boolean(string="Appear on Detail Payroll Report")
    add_to_calc_epf_etf = fields.Boolean(string="Add to Cal EPF/ETF", default=False)
