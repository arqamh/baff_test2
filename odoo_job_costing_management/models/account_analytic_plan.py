from odoo import models, fields, api


class AnalyticAccountPlan(models.Model):
    _inherit = 'account.analytic.plan'

    code = fields.Char(string='Code')