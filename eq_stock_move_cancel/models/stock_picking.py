from odoo import models, fields


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    def btn_reset_to_draft(self):
        for picking in self:
            move_raw_ids = picking.move_ids.filtered(lambda x: x.state == 'cancel').sudo()
            move_raw_ids.write({'state': 'draft'})