from odoo import models, _
from odoo.exceptions import UserError


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def revert_stock_move(self):
        """Revert the stock move linked to this move line (and all sibling move lines),
        removing all related entries: move lines, valuation layers, journal entries,
        analytic lines, quant updates, and M2M links.

        Called from the stock move line form/list view.

        Usage:
            move_line = self.env['stock.move.line'].browse(<move_line_id>)
            move_line.revert_stock_move()

        WARNING: This is a destructive operation. Use only for correcting mistakes.
        """
        # Collect all parent stock moves from the selected move lines
        moves = self.mapped('move_id')
        if not moves:
            raise UserError(_("No stock move found for the selected move line(s)."))

        for move in moves:
            all_move_lines = move.move_line_ids

            # --- 1. Reverse quant reservations and done quantities ---
            for ml in all_move_lines:
                if ml.state == 'done' and ml.qty_done > 0:
                    self.env['stock.quant']._update_available_quantity(
                        ml.product_id,
                        ml.location_dest_id,
                        -ml.qty_done,
                        lot_id=ml.lot_id,
                        package_id=ml.result_package_id,
                        owner_id=ml.owner_id,
                    )
                    self.env['stock.quant']._update_available_quantity(
                        ml.product_id,
                        ml.location_id,
                        ml.qty_done,
                        lot_id=ml.lot_id,
                        package_id=ml.package_id,
                        owner_id=ml.owner_id,
                    )

            # --- 2. Remove analytic lines ---
            if move.analytic_account_line_id:
                move.analytic_account_line_id.unlink()

            # --- 3. Remove journal entries via valuation layers ---
            valuation_layers = self.env['stock.valuation.layer'].search([
                ('stock_move_id', '=', move.id),
            ])
            if valuation_layers:
                account_moves = valuation_layers.mapped('account_move_id')
                posted_moves = account_moves.filtered(lambda m: m.state == 'posted')
                if posted_moves:
                    posted_moves.button_draft()
                account_moves.with_context(force_delete=True).unlink()
                valuation_layers.unlink()

            # --- 4. Remove any remaining journal entries linked to the stock move ---
            remaining_account_moves = self.env['account.move'].search([
                ('stock_move_id', '=', move.id),
            ])
            if remaining_account_moves:
                posted = remaining_account_moves.filtered(lambda m: m.state == 'posted')
                if posted:
                    posted.button_draft()
                remaining_account_moves.with_context(force_delete=True).unlink()

            # --- 5. Remove M2M links (move chains) ---
            move.move_dest_ids = [(5, 0, 0)]
            move.move_orig_ids = [(5, 0, 0)]
            move.route_ids = [(5, 0, 0)]

            # --- 6. Remove consume/produce traceability on move lines ---
            for ml in all_move_lines:
                ml.consume_line_ids = [(5, 0, 0)]
                ml.produce_line_ids = [(5, 0, 0)]

            # --- 7. Force state to draft via SQL to bypass ORM unlink constraints ---
            if all_move_lines:
                self.env.cr.execute(
                    "UPDATE stock_move_line SET state = 'draft' WHERE id IN %s",
                    [tuple(all_move_lines.ids)]
                )
                all_move_lines.invalidate_recordset(['state'])
                all_move_lines.unlink()

            # --- 8. Remove the stock move ---
            self.env.cr.execute(
                "UPDATE stock_move SET state = 'draft' WHERE id = %s",
                [move.id]
            )
            move.invalidate_recordset(['state'])
            move.unlink()
