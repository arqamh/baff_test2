from odoo import api, fields, models, _


class InheritMrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    def write(self, values):
        result = super(InheritMrpWorkorder, self).write(values)
        if values.get('date_planned_start') or values.get('date_planned_finished'):
            if self.move_raw_ids:
                for move in self.move_raw_ids:
                    if move.procurement_plan_id:
                        if move.procurement_plan_id.scheduled_date != move.workorder_id.date_planned_start.date():
                            other_mo_lines = self.env['stock.move'].search([]).filtered(
                                lambda x: x.procurement_plan_id.id == move.procurement_plan_id.id and x.id != move.id)
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
                                            'scheduled_date': move.workorder_id.date_planned_start.date(),
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
                                            'scheduled_date': move.workorder_id.date_planned_start.date(),
                                            'company_id': move.raw_material_production_id.company_id.id,
                                        })
                                        move.procurement_plan_id = other_mo_lines.procurement_plan_id.id
                            else:
                                move.procurement_plan_id.scheduled_date = move.workorder_id.date_planned_start.date()
                        else:
                            move.procurement_plan_id.scheduled_date = move.workorder_id.date_planned_start.date()
        return result
