# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

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
        string="Skip, Skip Installment Approval",
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


    @api.model
    def get_values(self):
        """
            Retrieves configuration values for loan management settings and updates the company-specific settings.
            The method fetches parameters related to loan guarantee configuration from the system configuration,
            and applies them to the current company as well as the settings view.

            Returns
            -------
            dict
                A dictionary containing updated configuration values relevant to loan management settings.
        """
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        company = self.env.company
        res.update(
            allow_max_guarantee_loans=params.get_param('centrics_hr_loan_management.allow_max_guarantee_loans'),
            max_guarantee_loans=params.get_param('centrics_hr_loan_management.max_guarantee_loans'),
            min_guarantors_required=params.get_param('centrics_hr_loan_management.min_guarantors_required'),
            no_of_minimum_guarantors=params.get_param('centrics_hr_loan_management.no_of_minimum_guarantors'),
            is_allow_manual_loan_settlement=params.get_param('centrics_hr_loan_management.is_allow_manual_loan_settlement'),
            is_skip_skip_installment_approval=params.get_param('centrics_hr_loan_management.is_skip_skip_installment_approval'),
            is_enable_payroll_integration=params.get_param('centrics_hr_loan_management.is_enable_payroll_integration'),
            use_basic_salary_as_max_loan=params.get_param('centrics_hr_loan_management.use_basic_salary_as_max_loan'),

        )

        company.update({
            'allow_max_guarantee_loans': params.get_param(
                'centrics_hr_loan_management.allow_max_guarantee_loans'),
            'max_guarantee_loans': params.get_param(
                'centrics_hr_loan_management.max_guarantee_loans'),
            'min_guarantors_required': params.get_param(
                'centrics_hr_loan_management.min_guarantors_required'),
            'no_of_minimum_guarantors': params.get_param(
                'centrics_hr_loan_management.no_of_minimum_guarantors'),
            'is_allow_manual_loan_settlement': params.get_param(
                'centrics_hr_loan_management.is_allow_manual_loan_settlement'),
            'is_skip_skip_installment_approval': params.get_param(
                'centrics_hr_loan_management.is_skip_skip_installment_approval'),
            'is_enable_payroll_integration': params.get_param(
                'centrics_hr_loan_management.is_enable_payroll_integration'),
            'use_basic_salary_as_max_loan': params.get_param(
                'centrics_hr_loan_management.use_basic_salary_as_max_loan')

        })
        return res

    def set_values(self):
        """
        Sets configuration values for the employee settings within the system.

        This method overrides the default set_values functionality to manage
        specific configurations related to employee management in the system.
        It ensures that the corresponding parameter values in the system's
        configuration are updated appropriately, including whether employee
        numbers are auto-generated and whether employee approval is required.

        Notes
        -----
        This method uses the `ir.config_parameter` model to persist configuration
        values in the database, ensuring these parameters are globally available
        throughout the system.

        Parameters
        ----------
        self : ResConfigSettings
            The instance of the configuration settings model where this method
            is being executed.

        Returns
        -------
        None
            This method does not return a value; it operates via side effects by
            updating system configuration parameters.
        """
        super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('centrics_hr_loan_management.allow_max_guarantee_loans', self.allow_max_guarantee_loans or False)
        params.set_param('centrics_hr_loan_management.max_guarantee_loans', self.max_guarantee_loans or 0)
        params.set_param('centrics_hr_loan_management.min_guarantors_required', self.min_guarantors_required or False)
        params.set_param('centrics_hr_loan_management.no_of_minimum_guarantors', self.no_of_minimum_guarantors or 0)
        params.set_param('centrics_hr_loan_management.is_allow_manual_loan_settlement', self.is_allow_manual_loan_settlement or False)
        params.set_param('centrics_hr_loan_management.is_skip_skip_installment_approval', self.is_skip_skip_installment_approval or False)
        params.set_param('centrics_hr_loan_management.is_enable_payroll_integration', self.is_enable_payroll_integration or False)
        params.set_param('centrics_hr_loan_management.use_basic_salary_as_max_loan', self.use_basic_salary_as_max_loan or False)
