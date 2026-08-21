# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class GrnRejectWizard(models.TransientModel):
    _name = 'grn.reject.wizard'
    _description = 'GRN Rejection Wizard'

    picking_id = fields.Many2one(
        'stock.picking', string='GRN', required=True, readonly=True)
    reason = fields.Text(string='Rejection Reason', required=True)
    remarks = fields.Text(string='Additional Remarks')

    def action_confirm_reject(self):
        self.ensure_one()
        if not self.reason or not self.reason.strip():
            raise UserError(_("A rejection reason is required."))
        self.picking_id.action_grn_reject(self.reason, self.remarks)
        return {'type': 'ir.actions.act_window_close'}
