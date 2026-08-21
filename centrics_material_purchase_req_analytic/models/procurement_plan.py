# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ProcurementPlan(models.Model):
    _name = 'procurement.plan'
    _inherit = [
        'analytic.mixin',
        'procurement.plan'
    ]


