from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import Warning, UserError


class PurchaseRequisition(models.Model):
    _inherit = 'material.purchase.requisition'

    @api.onchange('task_id')
    def onchange_project_task(self):
        """inbuilt function from the vendor"""
        for rec in self:
            rec.project_id = rec.task_id.project_id.id
            rec.analytic_account_id = rec.task_id.project_id.analytic_account_id.id
            rec.task_user_id = rec.task_id.user_ids[0].id if rec.task_id.user_ids else False

    @api.depends('requisition_line_ids', 'requisition_line_ids.product_id', 'requisition_line_ids.product_id.boq_type')
    def compute_equipment_machine(self):
        """FIXED: Initialize totals inside the loop to prevent cumulative values across records"""
        for rec in self:
            eqp_machine_total = 0.0
            work_resource_total = 0.0
            work_cost_package_total = 0.0
            subcontract_total = 0.0
            for line in rec.requisition_line_ids:
                cost = line.product_id.standard_price * line.qty
                boq_type = line.product_id.boq_type
                if boq_type == 'eqp_machine':
                    eqp_machine_total += cost
                elif boq_type == 'worker_resource':
                    work_resource_total += cost
                elif boq_type == 'work_cost_package':
                    work_cost_package_total += cost
                elif boq_type == 'subcontract':
                    subcontract_total += cost
            rec.equipment_machine_total = eqp_machine_total
            rec.worker_resource_total = work_resource_total
            rec.work_cost_package_total = work_cost_package_total
            rec.subcontract_total = subcontract_total

    task_id = fields.Many2one('project.task', string='Task / Job Order')
    task_user_id = fields.Many2one('res.users', string='Task / Job Order User')
    project_id = fields.Many2one('project.project', string='Construction Project')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    purchase_order_ids = fields.Many2many('purchase.order', string='Purchase Orders')
    equipment_machine_total = fields.Float(compute='compute_equipment_machine', string='Equipment / Machinery Cost',
                                           store=True)
    worker_resource_total = fields.Float(compute='compute_equipment_machine', string='Worker / Resource Cost',
                                         store=True)
    work_cost_package_total = fields.Float(compute='compute_equipment_machine', string='Work Cost Package', store=True)
    subcontract_total = fields.Float(compute='compute_equipment_machine', string='Subcontract Cost', store=True)
    job_costing_id = fields.Many2one('job.costing', string="Job Costing", compute='_compute_job_costing_id', store=True)

    def _compute_job_costing_id(self):
        for record in self:
            job_cost = False
            if record.requisition_line_ids:
                source = record.requisition_line_ids.mapped('job_costing_id')
                if source:
                    if len(source) == 1:
                        job_cost = source.id
            record.job_costing_id = job_cost

    @api.model
    def _prepare_po_line(self, line=False, purchase_order=False):
        """Override method and add job cost reference to the purchase order line
        OPTIMIZED: Use browse() instead of filtered() for single ID lookup"""
        res = super()._prepare_po_line(line=line, purchase_order=purchase_order)
        if res.get('custom_requisition_line_id'):
            # Direct browse is much faster than filtering entire recordset
            req_line = self.env['material.purchase.requisition.line'].browse(res.get('custom_requisition_line_id'))
            if req_line.exists():
                res.update({
                    'job_cost_id': req_line.job_costing_id.id,
                    'job_cost_line_id': req_line.job_cost_line_id.id,
                    'purchase_req_id': self.id,
                })
        return res

    @api.model
    def _prepare_pick_vals(self, line=False, stock_id=False):
        """Override stock Vals
        OPTIMIZED: Use browse() instead of filtered() for single ID lookup"""
        res = super()._prepare_pick_vals(line=line, stock_id=stock_id)
        if res.get('custom_requisition_line_id'):
            # Direct browse is much faster than filtering entire recordset
            req_line = self.env['material.purchase.requisition.line'].browse(res.get('custom_requisition_line_id'))
            if req_line.exists():
                res.update({
                    'job_cost_id': req_line.job_costing_id.id,
                    'job_cost_line_id': req_line.job_cost_line_id.id,
                })
        return res