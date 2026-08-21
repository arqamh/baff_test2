from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    procurement_plan_ids = fields.One2many('procurement.plan', 'mrp_id')

    def action_confirm(self):
        """Override confirm method and create procurement plan from components """
        response = super().action_confirm()
        procurement_obj = self.env['procurement.plan']
        for record in self:
            source = record
            source_name = False
            parent = record._get_sources()
            job_costing = False
            while parent:
                source = parent
                parent = parent._get_sources()
            if source.sale_order_id:
                if source.sale_order_id.job_costing_id:
                    source_name = source.sale_order_id.job_costing_id.display_name
                    job_costing = source.sale_order_id.job_costing_id
                else:
                    source_name = source.sale_order_id.name
            for components in record.move_raw_ids:
                if not components.created_production_id:
                    date = components.date.date()
                    if components.workorder_id:
                        if components.workorder_id.date_planned_start:
                            date = components.workorder_id.date_planned_start.date()
                    origin = source_name if source_name else source.name
                    existing_procurement = self.env['procurement.plan'].search(
                        [('source', '=', origin), ('product_id', '=', components.product_id.id),
                         ('scheduled_date', '=', date)])
                    job_cost_line = self.env['job.cost.line'].search([('bom_line_id', '=', components.bom_line_id.id)])
                    if job_cost_line:
                        job_cost_line[0].scheduled_date = date
                        components.job_cost_line_id = job_cost_line[0].id
                    if not existing_procurement:
                        product = self.env['product.product'].search([('id', '=', components.product_id.id)])
                        available_qty = product.qty_available
                        if available_qty < components.product_qty:
                            vals = {
                                'product_id': components.product_id.id,
                                'product_tml_id': components.product_tmpl_id.id if components.product_tmpl_id else False,
                                'mrp_id': components.raw_material_production_id.id,
                                'source': source_name if source_name else source.name,
                                'product_uom': components.product_uom.id,
                                'required_qty': components.product_qty,
                                'component_id': components.id,
                                'scheduled_date': date,
                                'company_id': components.raw_material_production_id.company_id.id,
                                'partner_id': components.job_cost_line_id.partner_id.id,
                            }
                            procurement_line = procurement_obj.create(vals)
                            if procurement_line:
                                components.procurement_plan_id = procurement_line.id
                    else:
                        existing_procurement.required_qty += components.product_qty
                        components.procurement_plan_id = existing_procurement.id
        return response

    def open_procurement_plans(self):
        """Open related procurement lines"""
        action = self.env['ir.actions.act_window']._for_xml_id('procurement_plan.action_procurement_plan_all')
        action['view_mode'] = 'tree,form'
        action['domain'] = [('id', 'in', self.procurement_plan_ids.ids)]
        return action

    def button_plan(self):
        """ Create work orders. And probably do stuff, like things. """
        result = super().button_plan()
        if self.move_raw_ids:
            for move in self.move_raw_ids:
                if move.procurement_plan_id:
                    planned_start_date = move.workorder_id.date_planned_start
                    if not planned_start_date:
                        raise UserError(_("Please add scheduled date to the operation"))
                    if move.procurement_plan_id.scheduled_date != planned_start_date.date():
                        other_mo_lines = self.env['stock.move'].search(
                            [('procurement_plan_id', '=', move.procurement_plan_id.id), ('id', '=', move.id)])
                        if other_mo_lines:
                            quantity = sum(other_mo_lines.mapped('product_qty'))
                            if quantity:
                                if not other_mo_lines.procurement_plan_id.forecasted_qty >= quantity:
                                    other_mo_lines.procurement_plan_id.required_qty = quantity
                                    vals = {
                                        'product_id': move.product_id.id,
                                        'product_tml_id': move.product_tmpl_id.id if move.product_tmpl_id else False,
                                        'mrp_id': move.raw_material_production_id.id,
                                        'source': other_mo_lines[0].procurement_plan_id.source,
                                        'product_uom': move.product_uom.id,
                                        'required_qty': move.product_qty,
                                        'component_id': move.id,
                                        'scheduled_date': planned_start_date.date(),
                                        'company_id': move.raw_material_production_id.company_id.id,
                                    }
                                    procurement_line = self.env['procurement.plan'].create(vals)
                                    if procurement_line:
                                        move.procurement_plan_id = procurement_line.id
                                else:
                                    other_mo_lines.procurement_plan_id.write({
                                        'mrp_id': move.raw_material_production_id.id,
                                        'source': other_mo_lines[0].procurement_plan_id.source,
                                        'product_uom': move.product_uom.id,
                                        'required_qty': move.product_qty,
                                        'component_id': move.id,
                                        'scheduled_date': planned_start_date.date(),
                                        'company_id': move.raw_material_production_id.company_id.id,
                                    })
                                    move.procurement_plan_id = other_mo_lines.procurement_plan_id.id
                        else:
                            move.procurement_plan_id.scheduled_date = planned_start_date.date()
                    else:
                        move.procurement_plan_id.scheduled_date = planned_start_date.date()
                if move.job_cost_line_id:
                    planned_start_date = move.workorder_id.date_planned_start
                    if not planned_start_date:
                        raise UserError(_("Please add scheduled date to the operation"))
                    move.job_cost_line_id.scheduled_date = planned_start_date.date()
        return result
