from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    procurement_plan_colors = fields.One2many(readonly=False, related="company_id.procurement_plan_colors" )


