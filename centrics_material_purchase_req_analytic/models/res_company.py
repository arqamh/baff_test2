# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    mrn_analytic_editable = fields.Boolean(
        string='MRN Analytic Editable',
        help='Enabling this option will allow you to edit the analytic details in Material requisition'
    )
