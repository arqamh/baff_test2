from odoo import fields, models, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    security_check = fields.Boolean(string='Security', default=False)


    def action_security_check(self):
        # security check button is true
        self.security_check = True

class StockMove(models.Model):
    _inherit = 'stock.move'

    job_cost_id = fields.Many2one('job.costing', string='Job Cost Center')
    job_cost_line_id = fields.Many2one('job.cost.line', string='Job Cost Line')