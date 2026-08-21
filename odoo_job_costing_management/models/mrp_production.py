from odoo import api, fields, models


class InheritMrpProduction(models.Model):
    _inherit = 'mrp.production'

    job_cost_id = fields.Many2one('job.costing', string="Costing Sheet")
    cost_analysis_line = fields.One2many(comodel_name='job.cost.line', inverse_name='mrp_id', copy=False)
    total_budget_cost = fields.Float(string="Total Budget Cost", related='job_cost_id.total_budget_cost')
    total_actual_cost = fields.Float(string="Total Actual Cost", related='job_cost_id.total_actual_cost')
    sale_order_id = fields.Many2one(related='job_cost_id.sale_id', string="Sales Order")

    @api.model
    def create(self, vals):
        """Overriding core method to set BOM to the MO and link the MO back
        to the matching finished-good line on the job costing sheet."""
        sales_order = self.env['sale.order'].search([('name', '=', vals.get('origin'))], limit=1)
        job_costing = sales_order.job_costing_id

        # Resolve a BOM that matches both the sheet and the MO product
        bom = self.env['mrp.bom']
        if job_costing and vals.get('product_id'):
            bom = self.env['mrp.bom'].search([
                ('job_cost_id', '=', job_costing.id),
                ('product_tmpl_id.product_variant_id', '=', vals.get('product_id')),
            ], order='id desc', limit=1)
            if bom:
                vals['bom_id'] = bom.id

        result = super().create(vals)

        # If the MO has a parent (kit/sub-assembly chain), inherit the parent's BOM/sheet
        parent_mo = result._get_sources()
        if parent_mo:
            if parent_mo.sale_order_id:
                parent_job_costing = parent_mo.sale_order_id.job_costing_id
                if parent_job_costing:
                    parent_bom = self.env['mrp.bom'].search([
                        ('job_cost_id', '=', parent_job_costing.id),
                        ('product_tmpl_id', '=', result.product_tmpl_id.id),
                    ], order='id desc', limit=1)
                    if parent_bom:
                        result.bom_id = parent_bom.id

        # Link MO to the sheet's matching finished-good line (replaces the old
        # single sheet.mrp_id field). Match by product_id.
        if job_costing:
            matching_fg = job_costing.finished_good_ids.filtered(
                lambda fg: fg.product_id.id == result.product_id.id)
            if matching_fg:
                result.job_cost_id = job_costing.id
                # If multiple finished-good lines share the same product, only
                # the first un-linked line gets the MO.
                target = matching_fg.filtered(lambda fg: not fg.mrp_production_id)[:1] or matching_fg[:1]
                target.mrp_production_id = result.id
        elif parent_mo and parent_mo.job_cost_id:
            result.job_cost_id = parent_mo.job_cost_id.id

        if result.job_cost_id:
            # Set finished good location as destination if available
            if result.job_cost_id.finished_good_location_id:
                result.location_dest_id = result.job_cost_id.finished_good_location_id.id
                for move in result.move_finished_ids:
                    move.location_dest_id = result.job_cost_id.finished_good_location_id.id

            if result.workorder_ids:
                # OPTIMIZED: Pre-group labour lines by (bom_display_name, work_center_id)
                # for O(1) lookup instead of O(n*m) filtered() per workorder
                labour_by_key = {}
                for cl in result.job_cost_id.job_labour_line_ids:
                    key = (cl.bom_id.display_name, cl.work_center_id.id)
                    if key not in labour_by_key:
                        labour_by_key[key] = cl
                bom_display = result.bom_id.display_name
                for workorder in result.workorder_ids:
                    cost_line = labour_by_key.get((bom_display, workorder.workcenter_id.id))
                    if cost_line:
                        workorder.date_planned_start = cost_line.operation_start_date
                        workorder.date_planned_finished = cost_line.operation_end_date

        return result
