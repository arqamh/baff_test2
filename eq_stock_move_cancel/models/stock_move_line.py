from odoo import models, fields


class stock_move_line(models.Model):
    _inherit = 'stock.move.line'

    def action_cancel_moves(self):
        for each in self:
            each.move_id._action_cancel()