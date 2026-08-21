# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright 2019 EquickERP
#
##############################################################################

from odoo import models, fields


class Stock_Move(models.Model):
    _inherit = 'stock.move'

    def _action_cancel(self):
        quant_obj = self.env['stock.quant']
        move_fields = self._fields.keys()
        for eachmove in self.filtered(lambda l: l.state == 'done'):
            if eachmove.product_id.type == 'product':
                for sm_line in eachmove.move_line_ids:
                    line_qty = sm_line.product_uom_id._compute_quantity(sm_line.qty_done, sm_line.product_id.uom_id)
                    quant_obj._update_available_quantity(sm_line.product_id, sm_line.location_id, line_qty, lot_id=sm_line.lot_id, package_id=sm_line.package_id, owner_id=sm_line.owner_id)
                    quant_obj._update_available_quantity(sm_line.product_id, sm_line.location_dest_id, line_qty * -1, lot_id=sm_line.lot_id, package_id=sm_line.package_id, owner_id=sm_line.owner_id)
            if eachmove.procure_method == 'make_to_order' and not eachmove.move_orig_ids:
                eachmove.state = 'waiting'
            elif eachmove.move_orig_ids and not all(orig.state in ('done', 'cancel') for orig in eachmove.move_orig_ids):
                eachmove.state = 'waiting'
            else:
                eachmove.state = 'confirmed'
            if eachmove.scrap_ids:
                eachmove.scrap_ids.write({'state': 'cancel'})
            if eachmove.account_move_ids:
                eachmove.account_move_ids.button_cancel()
                eachmove.account_move_ids.with_context(force_delete=True).unlink()
            if eachmove.stock_valuation_layer_ids:
                eachmove.stock_valuation_layer_ids.sudo().unlink()
            self._cr.execute("""DELETE FROM stock_valuation_layer
                                WHERE stock_move_id is Null
                                AND product_id = %s;""" % (eachmove.product_id.id))
            # new code
            eachmove.product_id._compute_value_svl()
            if eachmove.product_id.cost_method != 'standard':
                if eachmove.product_id.quantity_svl > 0:
                    ctx = {'default_product_id': eachmove.product_id.id,
                           'default_company_id': self.env.company.id}
                    wizard_id = self.env['stock.valuation.layer.revaluation'].with_context(ctx).create({'added_value': 0})
                    eachmove.product_id.sudo().write({'standard_price': wizard_id.new_value_by_qty})
                else:
                    eachmove.product_id.sudo().write({'standard_price': 0})
            eachmove.quantity_done = 0.00
        return super(Stock_Move, self)._action_cancel()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: