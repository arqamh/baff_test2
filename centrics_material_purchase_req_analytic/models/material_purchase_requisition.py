# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MaterialPurchaseRequisition(models.Model):
    _name = 'material.purchase.requisition'
    _inherit = [
        'analytic.mixin',
        'material.purchase.requisition'
    ]

    mp_project_id = fields.Many2one(
        'project.project',
        string='Project'
    )
    analytic_editable = fields.Boolean(
        'Analytic Editable',
        compute='_compute_analytic_editable',
        precompute=True
    )

    def _compute_analytic_editable(self):
        """
        @private - compute the analytic fields are editable
        """
        for rec in self:
            rec.update({
                'analytic_editable': rec.company_id.mrn_analytic_editable and rec.env.user.has_group('analytic.group_analytic_accounting')
            })

    @api.depends('mp_project_id')
    def _compute_analytic_distribution(self):
        """
        @private - compute analytic distribution related to project
        """
        for rec in self:
            assigned_analytic_account_ids = rec.env['account.analytic.account'].search([
                ('project_ids', 'in', rec.mp_project_id.id)
            ])
            analytic_distribution = {
                    analytic_account_id.id: 100
                    for analytic_account_id in assigned_analytic_account_ids
            }
            # Update material requisitions
            rec.update({
                'analytic_distribution': analytic_distribution
            })
            # Update material requisition lines
            rec.requisition_line_ids.update({
                'analytic_distribution': analytic_distribution
            })

    @api.model
    def _prepare_pick_vals(self, line=False, stock_id=False):
        """
        @override - adding analytic distribution values to stock moves
        """
        res = super()._prepare_pick_vals(line, stock_id)
        res.update({
            'analytic_distribution': self.analytic_distribution
        })
        return res

    def request_stock(self, line=False):
        """
        @override - adding analytic distribution values to picking
        """
        stock_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        for rec in self:
            stock_id = False
            if not rec.requisition_line_ids:
                raise UserError(_('Please create some requisition lines.'))

            if any(line.requisition_type == 'internal' for line in rec.requisition_line_ids):
                if not rec.custom_picking_type_id:
                    raise UserError(_('Select Picking Type under the picking details.'))
            source_location = []
            destination_location = {}
            lines = line if line else rec.requisition_line_ids
            for line in lines:
                if line.requisition_type == 'internal':
                    if not line.location_id:
                        raise UserError(_('Select Source location under the picking details.'))
                    if not line.dest_location_id:
                        raise UserError(_('Select Destination location under the picking details.'))
                    if not line.pr_state:
                        if (line.location_id.id, line.dest_location_id.id) not in source_location:
                            picking_vals = {
                                'partner_id': rec.employee_id.sudo().address_home_id.id,
                                'location_id': line.location_id.id,
                                'location_dest_id': line.dest_location_id and line.dest_location_id.id or rec.employee_id.dest_location_id.id or rec.employee_id.department_id.dest_location_id.id,
                                'picking_type_id': rec.custom_picking_type_id.id,
                                'note': rec.reason,
                                'custom_requisition_id': rec.id,
                                'origin': rec.name,
                                'company_id': rec.company_id.id,
                                'analytic_distribution': rec.analytic_distribution,  # Extended line
                            }
                            stock_id = stock_obj.sudo().create(picking_vals)
                            # delivery_vals = {'delivery_picking_id': stock_id.id}
                            # rec.write(delivery_vals)
                            pick_vals = rec._prepare_pick_vals(line, stock_id)
                            move_id = move_obj.sudo().create(pick_vals)
                            source_location.append((line.location_id.id, line.dest_location_id.id))
                            line.write({
                                'move_id': move_id.id
                            })
                        else:
                            pick_vals = rec._prepare_pick_vals(line, stock_id)
                            move_id = move_obj.sudo().create(pick_vals)
                            line.write({
                                'move_id': move_id.id
                            })
            rec.state = 'stock'

    @api.model
    def _prepare_po_line(self, line=False, purchase_order=False):
        """
        @override - adding analytic distribution tot the purchase order lines
        """
        res = super()._prepare_po_line(line, purchase_order)
        res.update({
            'analytic_distribution': self.analytic_distribution
        })
        return res
