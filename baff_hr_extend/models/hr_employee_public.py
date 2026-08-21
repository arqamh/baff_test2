# -*- coding: utf-8 -*-

from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    internal_note = fields.Text('Internal Notes')
    ocean_voyager_emp_category = fields.Selection([('staff', 'Staff'), ('non_staff', 'Non Staff')], string='Ocean Voyager Employee Category')
