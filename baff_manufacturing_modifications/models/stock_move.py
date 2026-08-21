from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    is_new_component = fields.Boolean(
        string='Is New Component',
        default=False,
        help='Flag to identify new components added during production that require approval'
    )

    def _prepare_procurement_values(self):
        """
        Override to propagate analytic account from parent manufacturing order
        to child manufacturing orders.

        When a raw material component needs to be manufactured (child MO),
        this ensures the parent MO's analytic account is passed through
        the procurement chain.
        """
        res = super()._prepare_procurement_values()
        # If this is a raw material move for a manufacturing order
        # and the MO has an analytic account, propagate it to child MOs
        if self.raw_material_production_id and self.raw_material_production_id.analytic_account_id:
            # Only set if not already set (e.g., by sale_mrp from sale order)
            if not res.get('analytic_account_id'):
                res['analytic_account_id'] = self.raw_material_production_id.analytic_account_id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """ Override create to automatically mark new components added to MO during production """
        moves = super(StockMove, self).create(vals_list)
        for move in moves:
            # Check if this is a component being added to an MO that's already in production
            if move.raw_material_production_id and not move.bom_line_id:
                # If the MO is already confirmed or in progress, this is a new component
                if move.raw_material_production_id.state in ('confirmed', 'progress', 'to_close'):
                    move.is_new_component = True
        return moves