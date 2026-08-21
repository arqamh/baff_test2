from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date, timedelta
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class StockUpdate(models.Model):
    _inherit = 'stock.move'


    move_date = fields.Date(string="Date")

    def _action_done(self, cancel_backorder=False):
        """Update stock valuation layer with backdate"""
        res = super(StockUpdate, self)._action_done()
        if not self._context.get('Skip'):
            custom_stock_picking_ids = self.env['stock.picking'].browse(self._context.get('active_id'))
            stock_type_id = self.env['stock.picking.type'].browse(self._context.get('active_id'))
            active_models1 = self._context.get('active_model')
            if active_models1 == 'stock.picking.type':
                if stock_type_id.code != 'outgoing':
                    for move in res:
                        move.write({'date': move.move_date or fields.Datetime.now()})
                        for line in move.mapped('move_line_ids'):
                            line.write({'date': move.move_date or fields.Datetime.now()})
                        for value in move.stock_valuation_layer_ids:
                            self.env.cr.execute(
                                """UPDATE stock_valuation_layer SET create_date=%s,product_id=%s,stock_move_id=%s,company_id=%s WHERE id=%s""",
                                (move.move_date or fields.Datetime.now(), value.product_id.id, value.stock_move_id.id,
                                 value.company_id.id, value.id))
                elif stock_type_id.code == 'outgoing':
                    for move in res:
                        move.write({'date': move.move_date or fields.Datetime.now()})
                        for line in move.mapped('move_line_ids'):
                            line.write({'date': move.move_date or fields.Datetime.now()})
                        for value in move.stock_valuation_layer_ids:
                            self.env.cr.execute(
                                """UPDATE stock_valuation_layer SET create_date=%s,product_id=%s,stock_move_id=%s,company_id=%s WHERE id=%s""",
                                (move.move_date or fields.Datetime.now(), value.product_id.id, value.stock_move_id.id,
                                 value.company_id.id, value.id))

            elif active_models1 == 'stock.picking':
                if custom_stock_picking_ids.picking_type_id.code != 'outgoing':
                    for move in res:
                        move.write({'date': move.move_date or fields.Datetime.now()})
                        for line in move.mapped('move_line_ids'):
                            line.write({'date': move.move_date or fields.Datetime.now()})
                        for value in move.stock_valuation_layer_ids:
                            self.env.cr.execute(
                                """UPDATE stock_valuation_layer SET create_date=%s,product_id=%s,stock_move_id=%s,company_id=%s WHERE id=%s""",
                                (move.move_date or fields.Datetime.now(), value.product_id.id, value.stock_move_id.id,
                                 value.company_id.id, value.id))

                elif custom_stock_picking_ids.picking_type_id.code == 'outgoing':
                    for move in res:
                        move.write({'date': move.move_date or fields.Datetime.now()})
                        for line in move.mapped('move_line_ids'):
                            line.write({'date': move.move_date or fields.Datetime.now()})
                        for value in move.stock_valuation_layer_ids:
                            self.env.cr.execute(
                                """UPDATE stock_valuation_layer SET create_date=%s,product_id=%s,stock_move_id=%s,company_id=%s WHERE id=%s""",
                                (move.move_date or fields.Datetime.now(), value.product_id.id, value.stock_move_id.id,
                                 value.company_id.id, value.id))

            elif active_models1 == 'stock.scrap':
                for move in res:
                    move.write({'date': move.move_date or fields.Datetime.now()})
                    for line in move.mapped('move_line_ids'):
                        line.write({'date': move.move_date or fields.Datetime.now()})
                    for value in move.stock_valuation_layer_ids:
                        self.env.cr.execute(
                            """UPDATE stock_valuation_layer SET create_date=%s,product_id=%s,stock_move_id=%s,company_id=%s WHERE id=%s""",
                            (move.move_date or fields.Datetime.now(), value.product_id.id, value.stock_move_id.id,
                             value.company_id.id, value.id))

            elif active_models1 == 'purchase.order':
                for move in res:
                    move.write({'date': move.move_date or fields.Datetime.now()})
                    for line in move.mapped('move_line_ids'):
                        line.write({'date': move.move_date or fields.Datetime.now()})
                    for value in move.stock_valuation_layer_ids:
                        self.env.cr.execute(
                            """UPDATE stock_valuation_layer SET create_date=%s,product_id=%s,stock_move_id=%s,company_id=%s WHERE id=%s""",
                            (move.move_date or fields.Datetime.now(), value.product_id.id, value.stock_move_id.id,
                             value.company_id.id, value.id))

            elif active_models1 == 'sale.order':
                for move in res:
                    move.write({'date': move.move_date or fields.Datetime.now()})
                    for line in move.mapped('move_line_ids'):
                        line.write({'date': move.move_date or fields.Datetime.now()})
                    for value in move.stock_valuation_layer_ids:
                        self.env.cr.execute(
                            """UPDATE stock_valuation_layer SET create_date=%s,product_id=%s,stock_move_id=%s,company_id=%s WHERE id=%s""",
                            (move.move_date or fields.Datetime.now(), value.product_id.id, value.stock_move_id.id,
                             value.company_id.id, value.id))

        return res

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id,cost):
        """Override move value method and update with stock scheduled date"""
        res = super()._prepare_account_move_vals(credit_account_id, debit_account_id, journal_id, qty, description, svl_id,cost)
        if self.env.context.get('force_back_date') and self.picking_id:
            res['date'] = self.picking_id.scheduled_date
        return res
