# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class MrpUnbuild(models.Model):
    _inherit = 'mrp.unbuild'

    state = fields.Selection(
        selection_add=[('reversed', 'Reversed')],
        ondelete={'reversed': 'set default'}
    )

    reverse_move_ids = fields.One2many(
        'stock.move',
        'reverse_unbuild_id',
        string='Reverse Stock Moves',
        readonly=True
    )

    is_reversed = fields.Boolean(
        string='Is Reversed',
        compute='_compute_is_reversed',
        store=True
    )

    reversed_date = fields.Datetime(
        string='Reversed Date',
        readonly=True,
        copy=False
    )

    reversed_by = fields.Many2one(
        'res.users',
        string='Reversed By',
        readonly=True,
        copy=False
    )

    @api.depends('state')
    def _compute_is_reversed(self):
        for unbuild in self:
            unbuild.is_reversed = unbuild.state == 'reversed'

    def action_reverse(self):
        """
        Reverse the unbuild order by creating reverse stock moves.
        This will:
        1. Create reverse moves for all consume moves (return consumed product to original location)
        2. Create reverse moves for all produce moves (return components back)
        3. Set the unbuild order state to 'reversed'
        4. Post a message to the related MO if exists
        """
        self.ensure_one()

        if self.state != 'done':
            raise UserError(_('Only completed unbuild orders can be reversed.'))

        # Check if already reversed
        if self.state == 'reversed':
            raise UserError(_('This unbuild order has already been reversed.'))

        # Check for existing reverse moves
        if self.reverse_move_ids.filtered(lambda m: m.state == 'done'):
            raise UserError(_('This unbuild order already has completed reverse moves.'))

        reverse_moves = self.env['stock.move']

        # Reverse consume moves (moves that consumed the finished product)
        # These moves took the finished product from stock location to production location
        # We need to reverse: production location -> stock location
        for consume_move in self.consume_line_ids.filtered(lambda m: m.state == 'done'):
            reverse_move = self._create_reverse_move(consume_move)
            reverse_moves |= reverse_move

        # Reverse produce moves (moves that produced components)
        # These moves produced components from production location to stock location
        # We need to reverse: stock location -> production location
        for produce_move in self.produce_line_ids.filtered(lambda m: m.state == 'done'):
            reverse_move = self._create_reverse_move(produce_move)
            reverse_moves |= reverse_move

        if not reverse_moves:
            raise UserError(_('No stock moves found to reverse.'))

        # Confirm and execute the reverse moves
        reverse_moves._action_confirm()

        # Set quantities for reverse moves based on original move lines
        for reverse_move in reverse_moves:
            original_move = reverse_move.origin_returned_move_id
            if original_move.move_line_ids:
                for original_line in original_move.move_line_ids:
                    self.env['stock.move.line'].create({
                        'move_id': reverse_move.id,
                        'product_id': reverse_move.product_id.id,
                        'product_uom_id': reverse_move.product_uom.id,
                        'location_id': reverse_move.location_id.id,
                        'location_dest_id': reverse_move.location_dest_id.id,
                        'qty_done': original_line.qty_done,
                        'lot_id': original_line.lot_id.id if original_line.lot_id else False,
                        'package_id': original_line.result_package_id.id if original_line.result_package_id else False,
                        'result_package_id': original_line.package_id.id if original_line.package_id else False,
                        'owner_id': original_line.owner_id.id if original_line.owner_id else False,
                    })
            else:
                # If no move lines, set quantity_done directly
                reverse_move.quantity_done = original_move.quantity_done

        # Execute the reverse moves
        reverse_moves._action_done()

        # Update the unbuild order state
        self.write({
            'state': 'reversed',
            'reversed_date': fields.Datetime.now(),
            'reversed_by': self.env.user.id,
        })

        # Post message to the original manufacturing order
        if self.mo_id:
            self.mo_id.message_post(
                body=_('Unbuild order %s has been reversed. Quantity: %s %s') % (
                    self.name,
                    self.product_qty,
                    self.product_uom_id.name
                )
            )

        # Post message to the unbuild order
        self.message_post(
            body=_('Unbuild order has been reversed by %s. %d stock moves were reversed.') % (
                self.env.user.name,
                len(reverse_moves)
            )
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Unbuild order %s has been reversed successfully.') % self.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def _create_reverse_move(self, original_move):
        """
        Create a reverse stock move for the given original move.
        The reverse move swaps source and destination locations.
        """
        return self.env['stock.move'].create({
            'name': _('Reverse: %s') % original_move.name,
            'product_id': original_move.product_id.id,
            'product_uom_qty': original_move.product_uom_qty,
            'product_uom': original_move.product_uom.id,
            'location_id': original_move.location_dest_id.id,
            'location_dest_id': original_move.location_id.id,
            'origin': _('Reverse of %s') % self.name,
            'reverse_unbuild_id': self.id,
            'origin_returned_move_id': original_move.id,
            'company_id': self.company_id.id,
            'state': 'draft',
            'procure_method': 'make_to_stock',
            'picking_type_id': original_move.picking_type_id.id if original_move.picking_type_id else False,
        })

    def action_view_reverse_moves(self):
        """
        Open a view showing all reverse stock moves for this unbuild order.
        """
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('stock.stock_move_action')
        action['domain'] = [('reverse_unbuild_id', '=', self.id)]
        action['context'] = dict(self.env.context, create=False)
        return action


class StockMove(models.Model):
    _inherit = 'stock.move'

    reverse_unbuild_id = fields.Many2one(
        'mrp.unbuild',
        string='Reverse Unbuild Order',
        check_company=True,
        index=True
    )
