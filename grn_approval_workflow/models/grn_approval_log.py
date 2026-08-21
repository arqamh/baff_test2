# -*- coding: utf-8 -*-
from odoo import fields, models


class GrnApprovalLog(models.Model):
    _name = 'grn.approval.log'
    _description = 'GRN Approval History'
    _order = 'event_date desc, id desc'

    picking_id = fields.Many2one(
        'stock.picking', string='GRN', required=True, ondelete='cascade',
        index=True)
    action = fields.Selection(
        [('submit', 'Submitted'),
         ('approve', 'Approved'),
         ('reject', 'Rejected')],
        string='Action', required=True)
    user_id = fields.Many2one(
        'res.users', string='User', required=True,
        default=lambda self: self.env.uid)
    event_date = fields.Datetime(
        string='Date', required=True, default=fields.Datetime.now)
    reason = fields.Text(string='Reason')
    remarks = fields.Text(string='Remarks')
