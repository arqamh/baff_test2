# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

NO_OF_DAYS = [
    ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'),
    ('9', '9'), ('10', '10'), ('11', '11'), ('12', '12'), ('13', '13'), ('14', '14'), ('15', '15'),
    ('16', '16'), ('17', '17'), ('18', '18'), ('19', '19'), ('20', '20'), ('21', '21'), ('22', '22'),
    ('23', '23'), ('24', '24'), ('25', '25'), ('26', '26'), ('27', '27'), ('28', '28'), ('29', '29'),
    ('30', '30'), ('31', '31')
]


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_standard_day_for_payroll = fields.Boolean(string="Is Standard Day for Payroll")
    standard_payroll_day = fields.Selection(selection=NO_OF_DAYS, string="Standard Payroll Day")
    skip_work_entry_validation = fields.Boolean(
        related='company_id.skip_work_entry_validation',
        readonly=False,
        string='Skip Work Entry Validation'
    )

    @api.model
    def get_values(self):
        """
            Retrieves configuration values for the payroll settings and updates the company-specific
            attributes with the retrieved data. This method is used to manage and synchronize payroll
            configuration settings between the global settings and the company-specific configurations,
            ensuring accurate and consistent payroll behavior.

            Returns
            -------
            dict
                A dictionary containing the updated configuration values for payroll settings. This
                dictionary includes the values retrieved from the system configuration parameters.
        """
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        company = self.env.company
        res.update(
            is_standard_day_for_payroll=params.get_param('centrics_hr_payroll.is_standard_day_for_payroll'),
            standard_payroll_day=params.get_param('centrics_hr_payroll.standard_payroll_day'),

        )
        company.update({
            'is_standard_day_for_payroll': params.get_param(
                'centrics_hr_payroll.is_standard_day_for_payroll'),
            'standard_payroll_day': params.get_param('centrics_hr_payroll.standard_payroll_day'),
        })
        return res

    def set_values(self):
        """
        Sets the configuration values for payroll settings.

        This method updates the system configuration parameters related to payroll settings such as
        whether a standard day is required for payroll, the specific standard payroll day, and the
        necessity for employee approval.

        Parameters
        ----------
        self : ResConfigSettings
            The instance of the settings where payroll configuration values are managed.

        Notes
        -----
        This method ensures persistence of the values entered for payroll configuration in the system
        parameters model. Changes made through this method will directly influence system behavior
        regarding payroll processing.
        """
        super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        employee_approval_needed = self.employee_approval_needed or False
        params.set_param('centrics_hr_payroll.is_standard_day_for_payroll', self.is_standard_day_for_payroll or False)
        params.set_param('centrics_hr_payroll.standard_payroll_day', self.standard_payroll_day or False)
