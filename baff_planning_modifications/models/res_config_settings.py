from odoo import models, fields, api, _


class InheritResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    holiday_ot = fields.Float(related='company_id.holiday_ot', readonly=False)
    saturday_ot = fields.Float(related='company_id.saturday_ot', readonly=False)
    working_days_ot = fields.Float(related='company_id.working_days_ot', readonly=False)
