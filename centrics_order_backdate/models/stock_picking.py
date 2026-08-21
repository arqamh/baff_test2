from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date, timedelta
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        """Open backdate validation wizard when click button validate"""
        if self.env.context.get('manual_validate'):
            for order in self:
                context = self.env.context.copy()
                context.update({
                            'default_transfer_date': order.scheduled_date,
                            'default_picking_ids': [(4, order.id)],
                            'manual_validate': False,})
                if order.picking_type_id.code in ('internal', 'incoming', 'outgoing', 'mrp_operation'):
                    return {
                        'name': 'Confirm Backdate',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'backdate.validate.wizard.internal',
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'res_id': False,
                        'context': context,
                    }

                else:
                    return order.with_context(force_period_date=order.scheduled_date).button_validate()

        else:
            # for record in self:
            if self.env.context.get('force_back_date') or self.env.context.get('manual_validate'):
                for picking in self:
                    for move_line in picking.move_ids:
                        move_line.write({
                            'date': picking.scheduled_date,
                            'move_date': picking.scheduled_date,
                            'date_deadline': picking.scheduled_date
                        })

                        for valuation in move_line.stock_valuation_layer_ids:
                            self.env.cr.execute(
                                """UPDATE stock_valuation_layer SET create_date=%s, product_id=%s,stock_move_id=%s,company_id=%s WHERE id=%s""",
                                (picking.scheduled_date, valuation.product_id.id, valuation.stock_move_id.id,
                                 valuation.company_id.id, valuation.id))

                        for line in move_line.mapped('move_line_ids'):
                            line.write({
                                'date': picking.scheduled_date,
                            })
            return super(StockPicking, self).button_validate()

