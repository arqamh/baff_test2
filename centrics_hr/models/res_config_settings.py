# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    employee_approval_needed =  fields.Boolean (string="Employee Approval Needed")
    employee_number_auto_generate = fields.Boolean(string="Employee Number Auto Generate")
    retirement_age = fields.Integer(string="Retirement Age")
    enable_onboarding = fields.Boolean(string="Enable Onboarding")

    @api.model
    def get_values(self):
        """
            Retrieve configuration settings values and update corresponding company-specific properties.

            This method fetches configuration values related to employee-related functionalities, such as
            whether approval is needed or if employee numbers should be auto-generated. The values are
            retrieved from the configuration parameters and used to update both the general settings and
            company-specific settings.

            Returns
            -------
            dict
                A dictionary containing updated configuration values for employee approval and employee
                number auto-generation.
        """
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        company = self.env.company
        res.update(
            employee_approval_needed=params.get_param('centrics_hr.employee_approval_needed'),
            employee_number_auto_generate = params.get_param('centrics_hr.employee_number_auto_generate'),
            retirement_age = params.get_param('centrics_hr.retirement_age'),
            enable_onboarding = params.get_param('centrics_hr.enable_onboarding')
        )
        company.update({
            'employee_approval_needed': params.get_param(
                'centrics_hr.employee_approval_needed'),
            'employee_number_auto_generate': params.get_param('centrics_hr.employee_number_auto_generate'),
            'retirement_age': params.get_param('centrics_hr.retirement_age'),
            'enable_onboarding': params.get_param('centrics_hr.enable_onboarding')
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
        employee_approval_needed = self.employee_approval_needed or False
        params.set_param('centrics_hr.employee_number_auto_generate', self.employee_number_auto_generate)
        params.set_param('centrics_hr.employee_approval_needed', employee_approval_needed)
        params.set_param('centrics_hr.retirement_age', self.retirement_age or False)
        params.set_param('centrics_hr.enable_onboarding', self.enable_onboarding or False)
