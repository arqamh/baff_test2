# -*- coding: utf-8 -*-
"""
Extend Payroll configuration to enable/disable PAYEE tax usage globally.
"""
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    payee_tax_enabled = fields.Boolean(
        string="Enable PAYEE Tax",
        config_parameter="centrics_hr_payee_tax.payee_tax_enabled",
        help="If enabled, salary rules can use the PAYEE tax table to compute tax."
    )
