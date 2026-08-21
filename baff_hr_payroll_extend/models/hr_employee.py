# -*- coding: utf-8 -*-
import logging
from odoo import models

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def compute_payee_tax_amount(self, gross_amount):
        """Compute PAYE/APIT for the given gross amount.

        Reads bracket slabs from hr.payee.tax (centrics_hr_payee_tax module):
          - below    : amount <= amount_to
          - between  : amount_from <= amount <= amount_to
          - above    : amount >= amount_from

        Returns 0.0 if:
          - gross_amount is zero or negative
          - PAYEE tax feature is disabled in Payroll Settings
          - hr.payee.tax model is not installed
          - no bracket matches the amount (rate = 0 %)
        """
        self.ensure_one()

        try:
            amount = float(gross_amount or 0.0)
        except (TypeError, ValueError):
            amount = 0.0

        if amount <= 0.0:
            return 0.0

        # Respect the PAYEE tax on/off toggle (Payroll → Configuration → Settings)
        key = "centrics_hr_payee_tax.payee_tax_enabled"
        val = self.env["ir.config_parameter"].sudo().get_param(key, default="False")
        if val not in ("True", "true", "1", True):
            return 0.0

        # Guard: hr.payee.tax model requires centrics_hr_payee_tax to be installed
        if not self.env.registry.get("hr.payee.tax"):
            _logger.warning(
                "compute_payee_tax_amount: hr.payee.tax model not found. "
                "Install centrics_hr_payee_tax or disable the PAYEE tax setting."
            )
            return 0.0

        rate = self.env["hr.payee.tax"]._get_rate_for_amount(amount)
        return round(amount * (rate / 100.0), 2)
