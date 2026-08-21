from odoo import api, models, fields


class MrpWorkcenterProductivity(models.Model):
    _inherit = "mrp.workcenter.productivity"

    slot_id = fields.Many2one('planning.slot', string="Planning Slot")