# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mrn_analytic_editable = fields.Boolean(
        related='company_id.mrn_analytic_editable',
        readonly=False
    )
