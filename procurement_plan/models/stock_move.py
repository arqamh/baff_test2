from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    procurement_plan_id = fields.Many2one('procurement.plan', ondelete="cascade")
    job_cost_line_id = fields.Many2one('job.cost.line', ondelete="cascade")