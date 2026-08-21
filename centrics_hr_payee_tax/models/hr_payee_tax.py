# -*- coding: utf-8 -*-
"""
PAYEE tax configuration model.

This model lets payroll users define bracket-based tax rates with three
condition types and plain float bounds:
- below: up to and including an upper bound
- between: inclusive lower and upper bounds
- above: from a lower bound upward

No company, currency, or active toggle is used. This table acts globally.
"""
from typing import Optional

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrPayeeTax(models.Model):
    _name = "hr.payee.tax"
    _description = "HR PAYEE Tax Bracket"
    _order = "sequence, amount_from, amount_to"

    sequence = fields.Integer(default=10, help="Ordering in the list.")

    condition_type = fields.Selection(
        selection=[
            ("below", "Below"),
            ("between", "Between"),
            ("above", "Above"),
        ],
        string="Condition",
        required=True,
        default="between",
        help="Type of condition to match against a taxable amount.",
    )
    amount_from = fields.Float(
        string="Amount From",
        help="Lower bound of the taxable amount (inclusive for 'between'/'above').",
    )
    amount_to = fields.Float(
        string="Amount To",
        help="Upper bound of the taxable amount (inclusive for 'below'/'between').",
    )
    percentage = fields.Float(
        string="Rate (%)",
        required=True,
        digits=(16, 4),
        help="Percentage rate to apply when this condition matches.",
    )

    @api.depends("condition_type", "amount_from", "amount_to", "percentage")
    def _compute_name(self):
        """Build a human-readable label for the bracket."""
        for rec in self:
            def fmt(v):
                try:
                    return f"{float(v):,.2f}"
                except Exception:
                    return "0.00"

            if rec.condition_type == "below":
                to_display = fmt(rec.amount_to) if rec.amount_to is not None else "--"
                rec.name = _("< = %s : %.2f%%") % (to_display, rec.percentage)
            elif rec.condition_type == "between":
                f_display = fmt(rec.amount_from) if rec.amount_from is not None else "--"
                to_display = fmt(rec.amount_to) if rec.amount_to is not None else "--"
                rec.name = _("%s - %s : %.2f%%") % (f_display, to_display, rec.percentage)
            else:
                f_display = fmt(rec.amount_from) if rec.amount_from is not None else "--"
                rec.name = _(">= %s : %.2f%%") % (f_display, rec.percentage)

    @api.constrains("condition_type", "amount_from", "amount_to", "percentage")
    def _check_values(self):
        """Validate logical consistency of bounds for each condition type."""
        for rec in self:
            if rec.percentage < 0.0:
                raise ValidationError(_("Rate (%%) cannot be negative."))

            if rec.condition_type == "below":
                if rec.amount_to is None:
                    raise ValidationError(_("For 'Below or equal', 'Amount To' is required."))
                if rec.amount_from and rec.amount_from > rec.amount_to:
                    raise ValidationError(_("For 'Below or equal', 'Amount From' cannot exceed 'Amount To'."))
            elif rec.condition_type == "between":
                if rec.amount_from is None or rec.amount_to is None:
                    raise ValidationError(_("For 'Between', both 'Amount From' and 'Amount To' are required."))
                if rec.amount_from > rec.amount_to:
                    raise ValidationError(_("For 'Between', 'Amount From' must be <= 'Amount To'."))
            elif rec.condition_type == "above":
                if rec.amount_from is None:
                    raise ValidationError(_("For 'Above or equal', 'Amount From' is required."))
                if rec.amount_to:
                    raise ValidationError(_("For 'Above or equal', 'Amount To' must be empty."))

    @api.constrains("condition_type", "amount_from", "amount_to")
    def _check_overlaps(self):
        """Prevent overlapping brackets globally (no company scoping)."""
        for rec in self:
            others = self.search([("id", "!=", rec.id)])
            for other in others:
                if _ranges_overlap(rec, other):
                    raise ValidationError(
                        _("Overlapping brackets are not allowed:\n- %s\n- %s")
                        % (rec.display_name, other.display_name)
                    )

    @api.model
    def _get_rate_for_amount(self, amount: float) -> float:
        """
        Return the matching percentage rate for a given taxable amount.
        If no bracket matches, returns 0.0.
        :param amount: The taxable amount to evaluate.
        :return: Percentage rate.
        """
        brackets = self.search([], order="sequence, amount_from, amount_to")
        for b in brackets:
            if b._matches(amount):
                return b.percentage
        return 0.0

    def _matches(self, amount: float) -> bool:
        """Check if the given amount is matched by this record's condition."""
        self.ensure_one()
        if self.condition_type == "below":
            if self.amount_to is None:
                return False
            return amount <= self.amount_to
        if self.condition_type == "between":
            if self.amount_from is None or self.amount_to is None:
                return False
            return self.amount_from <= amount <= self.amount_to
        # above
        if self.amount_from is None:
            return False
        return amount >= self.amount_from


def _ranges_overlap(a: "HrPayeeTax", b: "HrPayeeTax") -> bool:
    """Return True if brackets a and b overlap (global table)."""
    def bounds(rec):
        if rec.condition_type == "below":
            return (float("-inf"), rec.amount_to)
        if rec.condition_type == "between":
            return (rec.amount_from, rec.amount_to)
        # above
        return (rec.amount_from, float("inf"))

    a_lo, a_hi = bounds(a)
    b_lo, b_hi = bounds(b)
    if a_lo is None or a_hi is None or b_lo is None or b_hi is None:
        # If any bound is missing, be conservative and treat as overlapping
        return True
    # Overlap occurs when one's start <= the other's end AND one's end >= the other's start
    return (a_lo <= b_hi) and (a_hi >= b_lo)
