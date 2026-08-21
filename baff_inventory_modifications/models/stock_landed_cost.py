# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def action_reset_to_draft(self):
        """Reset landed cost from done/cancel state back to draft"""
        for cost in self:
            if cost.state == 'draft':
                raise UserError(_('This landed cost is already in draft state.'))

            # If the landed cost is in 'done' state, we need to reverse the accounting entries
            if cost.state == 'done':
                # Check if the accounting entry can be reset
                if cost.account_move_id:
                    if cost.account_move_id.state == 'posted':
                        raise UserError(_(
                            'Cannot reset to draft because the associated journal entry is posted. '
                            'Please reset the journal entry "%s" to draft first.'
                        ) % cost.account_move_id.name)

                    # Unlink the account move if it's in draft
                    cost.account_move_id.unlink()

                # Remove stock valuation layers created by this landed cost
                if cost.stock_valuation_layer_ids:
                    # Reverse the remaining value changes on linked layers
                    for svl in cost.stock_valuation_layer_ids:
                        if svl.stock_valuation_layer_id:
                            svl.stock_valuation_layer_id.sudo().write({
                                'remaining_value': svl.stock_valuation_layer_id.remaining_value - svl.value
                            })

                    # Unlink the valuation layers (requires sudo for permissions)
                    cost.stock_valuation_layer_ids.sudo().unlink()

            # Reset the state to draft
            cost.write({
                'state': 'draft',
                'account_move_id': False,
            })

        return True
