# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_overtime = fields.Boolean(string="Enable Overtime")
    consider_buffer_time = fields.Boolean(string="Consider Buffer Time")
    buffer_time = fields.Integer(string="Buffer Time")
    roundup_overtime = fields.Boolean(string="Roundup Overtime")
    roundup_overtime_interval = fields.Integer(string="Roundup Overtime Interval(Minutes)")
    deduct_late_check_in = fields.Boolean(string="Deduct Late Check In ?")
    consider_early_check_in = fields.Boolean(string="Consider Early Check In ?")
    need_to_approve = fields.Boolean(string="Approval Needed for Overtime ?")
    enable_inline_approval =  fields.Boolean(string="Enable Overtime Inline Approval")
    enable_bulk_approval =  fields.Boolean(string="Enable Overtime Bulk Approval")
    enable_pre_approval =  fields.Boolean(string="Enable Overtime Pre Approval")

    @api.model
    def get_values(self):
        """
        Retrieve configuration values from the database, specifically related to the 'centrics_hr_overtime.enable_overtime' parameter.
        This function fetches the parameter value indicating whether overtime functionality is enabled and updates it in the response dictionary
        as well as the company dictionary.

        Returns
        -------
        dict
            A dictionary containing the configuration values retrieved, updated with the 'enable_overtime' parameter.
        """
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        company = self.env.company
        res.update(
            enable_overtime=params.get_param('centrics_hr_overtime.enable_overtime'),
            consider_buffer_time=params.get_param('centrics_hr_overtime.consider_buffer_time'),
            buffer_time=params.get_param('centrics_hr_overtime.buffer_time'),
            need_to_approve=params.get_param('centrics_hr_overtime.need_to_approve'),
            enable_inline_approval=params.get_param('centrics_hr_overtime.enable_inline_approval'),
            enable_bulk_approval=params.get_param('centrics_hr_overtime.enable_bulk_approval'),
            enable_pre_approval=params.get_param('centrics_hr_overtime.enable_pre_approval'),
            deduct_late_check_in=params.get_param('centrics_hr_overtime.deduct_late_check_in'),
            consider_early_check_in=params.get_param('centrics_hr_overtime.consider_early_check_in'),
            roundup_overtime=params.get_param('centrics_hr_overtime.roundup_overtime'),
            roundup_overtime_interval=params.get_param('centrics_hr_overtime.roundup_overtime_interval'),
        )
        company.update({
            'enable_overtime': params.get_param(
                'centrics_hr_overtime.enable_overtime'),
            'consider_buffer_time': params.get_param(
                'centrics_hr_overtime.consider_buffer_time'),
            'buffer_time': params.get_param(
                'centrics_hr_overtime.buffer_time'),
            'need_to_approve': params.get_param(
                'centrics_hr_overtime.need_to_approve'),
            'enable_inline_approval': params.get_param(
                'centrics_hr_overtime.enable_inline_approval'),
            'enable_bulk_approval': params.get_param(
                'centrics_hr_overtime.enable_bulk_approval'),
            'enable_pre_approval': params.get_param(
                'centrics_hr_overtime.enable_pre_approval'),
            'deduct_late_check_in': params.get_param(
                'centrics_hr_overtime.deduct_late_check_in'),
            'roundup_overtime': params.get_param(
                'centrics_hr_overtime.roundup_overtime'),
            'roundup_overtime_interval': params.get_param(
                'centrics_hr_overtime.roundup_overtime_interval')
        })
        return res

    def set_values(self):
        """
        Sets configuration parameters for enabling overtime functionality.

        This method updates the configuration settings for the overtime module by
        modifying the value of the 'centrics_hr_overtime.enable_overtime' parameter
        in the system configuration.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('centrics_hr_overtime.enable_overtime', self.enable_overtime or False)
        params.set_param('centrics_hr_overtime.consider_buffer_time', self.consider_buffer_time or False)
        params.set_param('centrics_hr_overtime.buffer_time', self.buffer_time or False)
        params.set_param('centrics_hr_overtime.need_to_approve', self.need_to_approve or False)
        params.set_param('centrics_hr_overtime.enable_inline_approval', self.enable_inline_approval or False)
        params.set_param('centrics_hr_overtime.enable_bulk_approval', self.enable_bulk_approval or False)
        params.set_param('centrics_hr_overtime.enable_pre_approval', self.enable_pre_approval or False)
        params.set_param('centrics_hr_overtime.deduct_late_check_in', self.deduct_late_check_in or False)
        params.set_param('centrics_hr_overtime.consider_early_check_in', self.consider_early_check_in or False)
        params.set_param('centrics_hr_overtime.roundup_overtime', self.roundup_overtime or False)
        params.set_param('centrics_hr_overtime.roundup_overtime_interval', self.roundup_overtime_interval or False)

