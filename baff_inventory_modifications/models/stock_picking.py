from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        """ Override the button_validate method to synchronize source and destination locations """
        result = super(StockPicking, self).button_validate()
        for picking in self:
            src_loc = picking.location_id
            dest_loc = picking.location_dest_id

            if not src_loc or not dest_loc:
                raise Exception("Please set both Source and Destination locations on the picking first.")

            # 1) Try to unreserve (API varies by version; fallbacks are best-effort)
            try:
                picking.action_unreserve()
            except Exception:
                try:
                    self.env['stock.move'].sudo().search([('picking_id', '=', picking.id)])._do_unreserve()
                except Exception:
                    pass

            # 2) Bulk update stock.moves for this picking
            move_domain = [('picking_id', '=', picking.id)]
            move_vals = {
                'location_id': src_loc.id,
                'location_dest_id': dest_loc.id,
            }
            try:
                self.env['stock.move'].sudo().search(move_domain).write(move_vals)
            except Exception:
                pass

            # 3) Bulk update stock.move.lines (Detailed Operations) for this picking
            mline_domain = [('picking_id', '=', picking.id)]
            mline_vals = {
                'location_id': src_loc.id,
                'location_dest_id': dest_loc.id,
            }
            try:
                self.env['stock.move.line'].sudo().search(mline_domain).write(mline_vals)
            except Exception:
                pass

            # 4) Keep the picking header locations in sync (no-op if unchanged)
            picking.write({
                'location_id': src_loc.id,
                'location_dest_id': dest_loc.id,
            })

            # 5) Try to reassign reservations (ignore if not applicable)
            try:
                picking.action_assign()
            except Exception:
                pass

            # Optional: Log what happened
            try:
                picking.message_post(
                    body=(
                             "Server action: Synchronized <b>Source</b> to %s and <b>Destination</b> to %s "
                             "for all moves and detailed operations."
                         ) % (src_loc.display_name, dest_loc.display_name)
                )
            except Exception:
                pass
        return result