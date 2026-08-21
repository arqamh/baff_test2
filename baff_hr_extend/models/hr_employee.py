# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_number = fields.Char('Employee Number', related='epf_number', store=True)
    is_provident_fund_eligible = fields.Boolean(string="Eligible for EPF?", default=True)
    internal_note = fields.Text('Internal Notes', tracking=True)
    ocean_voyager_emp_category = fields.Selection([('staff', 'Staff'), ('non_staff', 'Non Staff')], string='Ocean Voyager Employee Category')
