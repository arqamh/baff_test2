# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    component_progress = fields.Float(
        string="Component Progress (%)",
        compute='_compute_component_progress',
    )
    operation_progress = fields.Float(
        string="Operation Progress (%)",
        compute='_compute_operation_progress',
    )
    overall_progress = fields.Float(
        string="Overall Progress (%)",
        compute='_compute_overall_progress',
    )
    child_mo_ids = fields.Many2many(
        'mrp.production',
        compute='_compute_child_mo_ids',
        string="Child Manufacturing Orders",
    )
    total_component_progress = fields.Float(
        string="Total Component Progress (%)",
        compute='_compute_total_progress',
    )
    total_operation_progress = fields.Float(
        string="Total Operation Progress (%)",
        compute='_compute_total_progress',
    )
    total_overall_progress = fields.Float(
        string="Total Overall Progress (%)",
        compute='_compute_total_progress',
    )

    @api.depends('move_raw_ids.state', 'move_raw_ids.product_uom_qty',
                 'move_raw_ids.quantity_done', 'state')
    def _compute_component_progress(self):
        for production in self:
            production.component_progress = production._calc_component_progress()

    @api.depends('workorder_ids.duration', 'workorder_ids.duration_expected',
                 'workorder_ids.state', 'state')
    def _compute_operation_progress(self):
        for production in self:
            production.operation_progress = production._calc_operation_progress()

    @api.depends('component_progress', 'operation_progress')
    def _compute_overall_progress(self):
        for production in self:
            production.overall_progress = production._calc_overall_progress(
                production.component_progress,
                production.operation_progress,
            )

    def _compute_child_mo_ids(self):
        for production in self:
            production.child_mo_ids = production._get_all_descendants()

    @api.depends('child_mo_ids', 'component_progress', 'operation_progress',
                 'child_mo_ids.component_progress', 'child_mo_ids.operation_progress')
    def _compute_total_progress(self):
        for production in self:
            all_mos = production | production.child_mo_ids
            # Aggregate across all non-cancelled MOs using weighted sums
            total_comp_done = 0.0
            total_comp_qty = 0.0
            total_op_duration = 0.0
            total_op_expected = 0.0
            has_any_components = False
            has_any_operations = False
            for mo in all_mos:
                if mo.state in ('draft', 'cancel'):
                    continue
                if mo.state == 'done':
                    # Done MOs contribute their full raw move quantities as 100% done
                    moves = mo.move_raw_ids.filtered(lambda m: m.state != 'cancel')
                    qty = sum(moves.mapped('product_uom_qty')) if moves else 0.0
                    if qty:
                        total_comp_done += qty
                        total_comp_qty += qty
                        has_any_components = True
                    workorders = mo.workorder_ids.filtered(lambda w: w.state != 'cancel')
                    expected = sum(workorders.mapped('duration_expected')) if workorders else 0.0
                    if expected:
                        total_op_duration += expected
                        total_op_expected += expected
                        has_any_operations = True
                else:
                    moves = mo.move_raw_ids.filtered(lambda m: m.state != 'cancel')
                    if moves:
                        total_comp_qty += sum(moves.mapped('product_uom_qty'))
                        total_comp_done += sum(moves.mapped('quantity_done'))
                        has_any_components = True
                    workorders = mo.workorder_ids.filtered(lambda w: w.state != 'cancel')
                    if workorders:
                        total_op_expected += sum(workorders.mapped('duration_expected'))
                        total_op_duration += sum(workorders.mapped('duration'))
                        has_any_operations = True

            comp_pct = min(total_comp_done / total_comp_qty * 100.0, 100.0) if total_comp_qty else 0.0
            op_pct = min(total_op_duration / total_op_expected * 100.0, 100.0) if total_op_expected else 0.0
            production.total_component_progress = comp_pct
            production.total_operation_progress = op_pct
            # Smart average for total overall
            if has_any_components and has_any_operations:
                production.total_overall_progress = (comp_pct + op_pct) / 2.0
            elif has_any_components:
                production.total_overall_progress = comp_pct
            elif has_any_operations:
                production.total_overall_progress = op_pct
            else:
                production.total_overall_progress = 0.0

    def _calc_component_progress(self):
        """Calculate component progress for a single production order."""
        self.ensure_one()
        if self.state == 'done':
            return 100.0
        if self.state in ('draft', 'cancel'):
            return 0.0
        moves = self.move_raw_ids.filtered(lambda m: m.state != 'cancel')
        if not moves:
            return 0.0
        total_qty = sum(moves.mapped('product_uom_qty'))
        if not total_qty:
            return 0.0
        done_qty = sum(moves.mapped('quantity_done'))
        return min(done_qty / total_qty * 100.0, 100.0)

    def _calc_operation_progress(self):
        """Calculate operation progress for a single production order."""
        self.ensure_one()
        if self.state == 'done':
            return 100.0
        if self.state in ('draft', 'cancel'):
            return 0.0
        workorders = self.workorder_ids.filtered(lambda w: w.state != 'cancel')
        if not workorders:
            return 0.0
        total_expected = sum(workorders.mapped('duration_expected'))
        if not total_expected:
            return 0.0
        total_duration = sum(workorders.mapped('duration'))
        return min(total_duration / total_expected * 100.0, 100.0)

    def _calc_overall_progress(self, comp_progress, op_progress):
        """Smart average: uses both if both exist, or just the available one."""
        self.ensure_one()
        if self.state == 'done':
            return 100.0
        if self.state in ('draft', 'cancel'):
            return 0.0
        has_components = bool(self.move_raw_ids.filtered(lambda m: m.state != 'cancel'))
        has_operations = bool(self.workorder_ids.filtered(lambda w: w.state != 'cancel'))
        if has_components and has_operations:
            return (comp_progress + op_progress) / 2.0
        if has_components:
            return comp_progress
        if has_operations:
            return op_progress
        return 0.0

    def _get_all_descendants(self):
        """Iterative BFS to find all descendant MOs using core _get_children()."""
        self.ensure_one()
        all_children = self.env['mrp.production']
        current_level = self
        while True:
            next_level = self.env['mrp.production']
            for mo in current_level:
                next_level |= mo._get_children()
            # Remove already-found to avoid cycles
            new_children = next_level - all_children
            if not new_children:
                break
            all_children |= new_children
            current_level = new_children
        return all_children
