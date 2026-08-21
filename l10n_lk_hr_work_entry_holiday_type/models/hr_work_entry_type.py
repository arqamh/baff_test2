# -*- coding: utf-8 -*-
"""
Model extension for hr.work.entry.type to add local holiday mapping.
Complies with the rule: one class per file and Python file name equals class name.
"""
from odoo import api, fields, models


class HrWorkEntryType(models.Model):
    """Extend work entry types with a local holiday classification.

    This selection helps identify Public, Mercantile, Poya and similar days
    when applying payroll, overtime, or reporting rules.
    """
    _inherit = "hr.work.entry.type"

    holiday_mapping = fields.Selection(
        selection=[
            ("none", "— Not a Holiday —"),
            ("public", "Public Holiday"),
            ("mercantile", "Mercantile Holiday"),
            ("poya", "Poya Day"),
            ("religious", "Religious Holiday (Other)"),
            ("company", "Company Holiday"),
        ],
        string="Holiday Mapping",
        default="none",
        help="Localize this Work Entry Type by the applicable holiday category.",
        tracking=True,  # Track changes on chatter as per guideline.
    )

    @api.onchange("holiday_mapping")
    def _onchange_holiday_mapping(self):
        """Hook for future behavior based on selected mapping.

        Currently no side-effects; kept to show where extra logic could go.
        """
        # Intentionally left blank to keep behavior explicit.
        return