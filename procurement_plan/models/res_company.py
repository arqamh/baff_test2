from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    procurement_plan_colors = fields.One2many('procurement.plan.color', 'company_id')