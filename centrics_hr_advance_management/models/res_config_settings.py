from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_advance_approval = fields.Boolean(
        string="Employee Advance Approval",
    )
    enable_payroll_integration = fields.Boolean(string="Enable Payroll Integration", help="Enable this option to enable payroll integration.")

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
            enable_advance_approval=params.get_param('centrics_hr_advance_management.enable_advance_approval'),
            enable_payroll_integration=params.get_param('centrics_hr_advance_management.enable_payroll_integration'),

        )

        company.update({
            'enable_advance_approval': params.get_param(
                'centrics_hr_advance_management.enable_advance_approval'),
            'enable_payroll_integration': params.get_param(
                'centrics_hr_advance_management.enable_payroll_integration'),
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
        (params.set_param('centrics_hr_advance_management.enable_advance_approval',
                         self.enable_advance_approval or False),
         params.set_param('centrics_hr_advance_management.enable_payroll_integration',
                         self.enable_payroll_integration or False))
