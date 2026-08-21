# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """Inherit configurations settings class"""
    _inherit = 'res.config.settings'

    multiple_approval_method = fields.Selection([('one', 'At least one user must approve'), ('all', 'All users must approve')], string="Approval method",  help="Record approval method", default='one', config_parameter="centrics_user_approve.multiple_approval_method")
