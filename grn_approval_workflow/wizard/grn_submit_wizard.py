# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class GrnSubmitWizard(models.TransientModel):
    _name = 'grn.submit.wizard'
    _description = 'GRN Submit for Approval Wizard'

    picking_id = fields.Many2one(
        'stock.picking', string='GRN', required=True, readonly=True)
    approver_ids = fields.Many2many(
        'res.users', 'grn_submit_wizard_approver_rel',
        'wizard_id', 'user_id',
        string='Approvers',
        domain="[('share', '=', False)]",
        help='Resolved from the matching GRN Approval Configuration. '
             'Remove any approvers who are not required for this GRN.')
    note = fields.Char(
        default='Review the approvers below. Remove anyone not required, '
                'then click Submit.',
        readonly=True)

    def action_confirm_submit(self):
        self.ensure_one()
        if not self.approver_ids:
            raise UserError(_(
                "At least one approver is required to submit this GRN."))
        self.picking_id._perform_grn_submit(self.approver_ids)
        return {'type': 'ir.actions.act_window_close'}
