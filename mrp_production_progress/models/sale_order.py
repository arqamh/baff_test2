# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    mo_component_progress = fields.Float(
        string="MO Component Progress (%)",
        compute='_compute_mo_progress',
        help="Average component progress of all manufacturing orders linked to this sale order"
    )
    mo_operation_progress = fields.Float(
        string="MO Operation Progress (%)",
        compute='_compute_mo_progress',
        help="Average operation progress of all manufacturing orders linked to this sale order"
    )
    mo_overall_progress = fields.Float(
        string="MO Overall Progress (%)",
        compute='_compute_mo_progress',
        help="Average overall progress of all manufacturing orders linked to this sale order"
    )
    has_manufacturing_orders = fields.Boolean(
        string="Has Manufacturing Orders",
        compute='_compute_mo_progress',
        help="Indicates if this sale order has any manufacturing orders"
    )

    @api.depends('mrp_production_ids', 'mrp_production_ids.total_component_progress',
                 'mrp_production_ids.total_operation_progress', 'mrp_production_ids.total_overall_progress',
                 'mrp_production_ids.state')
    def _compute_mo_progress(self):
        """
        Compute the average progress of all manufacturing orders linked to this sale order.
        Uses the total progress (including child MOs) from each manufacturing order.
        Only considers non-cancelled manufacturing orders.
        """
        for order in self:
            # Get all non-cancelled manufacturing orders
            active_mos = order.mrp_production_ids.filtered(lambda mo: mo.state != 'cancel')

            if not active_mos:
                order.has_manufacturing_orders = False
                order.mo_component_progress = 0.0
                order.mo_operation_progress = 0.0
                order.mo_overall_progress = 0.0
            else:
                order.has_manufacturing_orders = True
                # Calculate average of total progress (which includes child MOs)
                order.mo_component_progress = sum(active_mos.mapped('total_component_progress')) / len(active_mos)
                order.mo_operation_progress = sum(active_mos.mapped('total_operation_progress')) / len(active_mos)
                order.mo_overall_progress = sum(active_mos.mapped('total_overall_progress')) / len(active_mos)
