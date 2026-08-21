from odoo import fields, models, api


class MrpRoutingWorkCenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    jobcost_line_id = fields.Many2one('job.cost.line', string="Job Cost Line")