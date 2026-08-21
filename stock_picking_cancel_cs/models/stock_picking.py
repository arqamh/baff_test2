from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    cancel_done_picking = fields.Boolean(
        string='Cancel Done Delivery?',
        compute='check_cancel_done_picking'
    )

    @api.depends_context('uid')
    def check_cancel_done_picking(self):

        for picking in self:
            if self.user_has_groups('stock_picking_cancel_cs.group_cancel_delivery_order'):
                picking.cancel_done_picking = True
            else:
                picking.cancel_done_picking = False

    def action_cancel(self):
        quant_obj = self.env['stock.quant']
        moves = self.env['account.move']
        return_picking_obj = self.env['stock.return.picking']
        account_move_obj = self.env['account.move']

        for picking in self:
            if self.env.context.get('Flag', False) and picking.state == 'done':
                account_moves = picking.move_ids
                for move in account_moves:
                    if move.state == 'cancel':
                        continue
                    landed_cost_rec = []
                    try:
                        landed_obj = self.env['stock.landed.cost']
                        landed_cost_rec = landed_obj.search([
                            ('picking_ids', '=', picking.id),
                            ('state', '=', 'done')
                        ])
                    except Exception:
                        pass

                    if landed_cost_rec:
                        raise ValidationError(
                            'This Delivery is set in landed cost record %s '
                            'you need to delete it first then you can cancel '
                            'this Delivery' % ','.join(
                                landed_cost_rec.mapped('name')
                            )
                        )

                    if move.state == "done" and move.product_id.type == "product":
                        for move_line in move.move_line_ids:
                            quantity = move_line.product_uom_id._compute_quantity(
                                move_line.qty_done,
                                move_line.product_id.uom_id
                            )
                            quant_obj._update_available_quantity(
                                move_line.product_id,
                                move_line.location_id,
                                quantity,
                                move_line.lot_id.id
                            )
                            quant_obj._update_available_quantity(
                                move_line.product_id,
                                move_line.location_dest_id,
                                quantity * -1,
                                move_line.lot_id.id
                            )
                    if (move.procure_method == 'make_to_order'
                            and not move.move_orig_ids):
                        move.state = 'waiting'
                    elif (move.move_orig_ids
                            and not all(orig.state in ('done', 'cancel')
                                        for orig in move.move_orig_ids)):
                        move.state = 'waiting'
                    else:
                        move.state = 'confirmed'
                    siblings_states = (
                        (move.move_dest_ids.mapped('move_orig_ids') - move)
                        .mapped('state')
                    )
                    if move.propagate_cancel:
                        # only cancel the next move if all my siblings
                        # are also cancelled
                        if all(state == 'cancel' for state in siblings_states):
                            move.move_dest_ids._action_cancel()
                    else:
                        if all(state in ('done', 'cancel')
                               for state in siblings_states):
                            move.move_dest_ids.write({
                                'procure_method': 'make_to_stock'
                            })
                        move.move_dest_ids.write({
                            'move_orig_ids': [(3, move.id, 0)]
                        })
                    move.write({
                        'state': 'cancel',
                        'move_orig_ids': [(5, 0, 0)]
                    })
                    account_moves = account_move_obj.search([
                        ('stock_move_id', '=', move.id)
                    ])
                    valuation = move.stock_valuation_layer_ids
                    valuation and valuation.sudo().unlink()
                    if account_moves:
                        for account_move in account_moves:
                            account_move.button_cancel()
                            account_move.line_ids.remove_move_reconcile()
                            account_move.with_context(
                                force_delete=True
                            ).unlink()

        res = super(StockPicking, self).action_cancel()
        return res

    def action_draft(self):
        for res in self:
            if res.state == 'cancel':
                res.state = 'draft'
                res.move_ids.write({'state': 'draft'})
                if res.move_ids.move_line_ids:
                    for mvl in res.move_ids.move_line_ids:
                        mvl.write({'qty_done': 0.00})
                res.is_locked = False

        return True
