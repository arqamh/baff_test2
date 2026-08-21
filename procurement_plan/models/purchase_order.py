from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    procurement_plan_line_count = fields.Integer(compute="compute_procurement_plan_line_count")

    def compute_procurement_plan_line_count(self):
        """Count related procurement line count order lines"""
        for record in self:
            record.procurement_plan_line_count = len(record.order_line.mapped('procurement_plan_ids'))

    def action_view_procurement_plans(self):
        """action for open related procurement plan lines """
        action = self.env['ir.actions.act_window']._for_xml_id('procurement_plan.action_procurement_plan_all')
        action['view_mode'] = 'tree,form'
        action['domain'] = [('id', 'in', self.order_line.mapped('procurement_plan_ids').ids)]
        return action


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    procurement_plan_ids = fields.Many2many('procurement.plan', copy=False)
