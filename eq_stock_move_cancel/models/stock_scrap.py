from odoo import models, fields


class Stock_Scrap(models.Model):
    _inherit = 'stock.scrap'

    state = fields.Selection(selection_add=[('cancel', 'Cancel')])

    def btn_action_cancel(self):
        for scrap in self:
            if scrap.move_id:
                scrap.move_id._action_cancel()