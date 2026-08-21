from odoo import models, fields, api, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def compute_payee_tax_amount(self, gross_amount: float) -> float:
        """
        Compute PAYEE (APIT) tax amount for a given gross monthly amount.

        Logic:
        1) If PAYEE feature is disabled in Payroll Settings -> return 0.0.
        2) Normalize the input amount (None/invalid/<=0 -> 0.0).
        3) Fetch matching rate (%) from hr.payee.tax table.
        4) Return rounded tax amount: gross * (rate / 100).

        :param gross_amount: Monthly gross taxable amount.
        :return: Tax amount (float, rounded to 2 decimals).
        """
        self.ensure_one()

        # 1) Respect module toggle (Payroll → Configuration → Settings → PAYEE Tax)
        key = "centrics_hr_payee_tax.payee_tax_enabled"
        val = self.env["ir.config_parameter"].sudo().get_param(key, default="False")
        if val not in ("True", "true", "1", 1, True):
            return 0.0

        # 2) Normalize input
        try:
            amount = float(gross_amount or 0.0)
        except (TypeError, ValueError):
            amount = 0.0
        if amount <= 0.0:
            return 0.0

        # 3) Get matching rate (%) from configured brackets
        rate = self.env["hr.payee.tax"]._get_rate_for_amount(amount)

        # 4) Compute and round the tax amount
        return round(amount * (rate / 100.0), 2)
