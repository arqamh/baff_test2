from odoo import models,fields,api,_


class ResCompany(models.Model):
    _inherit = 'res.company'

    allow_max_guarantee_loans = fields.Boolean(
        string="Allow Max Guarantee Loans",
        help="Enable this option to allow loans with a maximum guarantee limit."
    )
    max_guarantee_loans = fields.Integer(
        string="Max Guarantee Loans",
        help="Specify the maximum number of guarantee loans an employee can take."
    )
    min_guarantors_required = fields.Boolean(
        string="Minimum Guarantors Required",
        help="Specify the minimum number of guarantors required for a loan"
    )
    no_of_minimum_guarantors = fields.Integer(
        string="No of Minimum Guarantors",
        help="Define the number of minimum guarantors required to approve a loan."
    )
    is_allow_manual_loan_settlement = fields.Boolean(
        string="Allow Manual Loan Settlement",
        help="Enable this option to allow manual loan settlement."
    )
    is_skip_skip_installment_approval = fields.Boolean(
        string="Skip Skip Installment Approval",
        help="Enable this option to skip the installment approval step."
    )
    is_enable_payroll_integration = fields.Boolean(
        string="Enable Payroll Integration",
        help="Enable this option to enable payroll integration."
    )
    use_basic_salary_as_max_loan = fields.Boolean(
        string="Use Basic Salary as Maximum Loan Amount",
        help="When enabled, if the loan type does not have a maximum loan amount configured, "
             "the employee's basic salary (contract wage) will be used as the maximum loan limit."
    )