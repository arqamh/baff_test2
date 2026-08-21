# -*- coding: utf-8 -*-
"""Extend hr.contract with computed OT rate fields for Ocean Voyager.

Rates are derived from the contract wage and the employee's Ocean Voyager
category (staff = 240 hrs/month, non-staff = 200 hrs/month).
"""
from odoo import api, fields, models

MONTHLY_HOURS = {
    'staff': 240.0,
    'non_staff': 200.0,
}


class HrContract(models.Model):
    _inherit = 'hr.contract'

    baff_ot_rate_normal = fields.Float(
        string="Normal OT Rate (/hour)",
        compute='_compute_baff_ot_rates',
        store=True,
    )
    baff_ot_rate_double = fields.Float(
        string="Double OT Rate (/hour)",
        compute='_compute_baff_ot_rates',
        store=True,
    )
    baff_ot_rate_triple = fields.Float(
        string="Triple OT Rate (/hour)",
        compute='_compute_baff_ot_rates',
        store=True,
    )

    @api.depends('wage', 'employee_id.ocean_voyager_emp_category')
    def _compute_baff_ot_rates(self):
        for contract in self:
            category = contract.employee_id.ocean_voyager_emp_category
            monthly_hours = MONTHLY_HOURS.get(category, 0.0)
            if contract.wage and monthly_hours:
                base_rate = contract.wage / monthly_hours
                contract.baff_ot_rate_normal = base_rate * 1.5
                contract.baff_ot_rate_double = base_rate * 2.0
                contract.baff_ot_rate_triple = base_rate * 3.0
            else:
                contract.baff_ot_rate_normal = 0.0
                contract.baff_ot_rate_double = 0.0
                contract.baff_ot_rate_triple = 0.0

    def action_recompute_baff_ot_rates(self):
        self._compute_baff_ot_rates()
        return True
