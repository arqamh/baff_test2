# -*- coding: utf-8 -*-
from odoo import api, fields, models


ACTION_SELECTION = [
    ('submit', 'Submit'),
    ('approve', 'Approve'),
    ('reject', 'Reject'),
]


class GrnApprovalConfig(models.Model):
    _name = 'grn.approval.config'
    _description = 'GRN Approval Configuration'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True)

    action_type = fields.Selection(
        ACTION_SELECTION,
        string='Workflow Action', required=True, default='submit',
        help='Which workflow event this configuration reacts to.\n'
             ' * Submit: triggered when a GRN is sent for approval — used to '
             'resolve approvers and notify them.\n'
             ' * Approve: triggered when a GRN is approved — used to notify '
             'recipients.\n'
             ' * Reject: triggered when a GRN is rejected — used to notify '
             'recipients.')

    picking_type_ids = fields.Many2many(
        'stock.picking.type', string='Operation Types',
        domain="[('code', '=', 'incoming')]",
        help='Restrict this configuration to specific incoming operation '
             'types. Leave empty to apply to all incoming transfers.')

    approver_user_ids = fields.Many2many(
        'res.users', 'grn_approval_config_approver_user_rel',
        'config_id', 'user_id', string='Approvers (Users)',
        domain="[('share', '=', False)]",
        help='Specific users allowed to approve / reject when this '
             'configuration matches. Only used for the "Submit" action; '
             'ignored for "Approve" and "Reject".')
    approver_group_ids = fields.Many2many(
        'res.groups', 'grn_approval_config_approver_group_rel',
        'config_id', 'group_id', string='Approvers (Roles)',
        help='User groups (roles) allowed to approve / reject when this '
             'configuration matches. Only used for the "Submit" action; '
             'ignored for "Approve" and "Reject".')

    recipient_user_ids = fields.Many2many(
        'res.users', 'grn_approval_config_recipient_user_rel',
        'config_id', 'user_id', string='Notification Recipients (Users)',
        domain="[('share', '=', False)]",
        help='Specific users to notify in addition to the configured groups.')
    recipient_group_ids = fields.Many2many(
        'res.groups', 'grn_approval_config_recipient_group_rel',
        'config_id', 'group_id', string='Notification Recipients (Roles)',
        help='User groups whose members will be notified.')
    notify_creator = fields.Boolean(
        string='Notify GRN Creator', default=True,
        help='When checked, the GRN creator receives the notification email '
             'in addition to other recipients. The system always notifies '
             'the creator for the Approve and Reject actions, regardless of '
             'this flag.')

    template_id = fields.Many2one(
        'mail.template', string='Email Template',
        domain="[('model', '=', 'stock.picking')]",
        help='Email template used for the notification. If empty, the '
             'module default template for this action is used.')

    notes = fields.Text(string='Notes')

    @api.model
    def _get_default_template(self, action_type):
        xmlid_map = {
            'submit': 'grn_approval_workflow.mail_template_grn_submit',
            'approve': 'grn_approval_workflow.mail_template_grn_approve',
            'reject': 'grn_approval_workflow.mail_template_grn_reject',
        }
        xmlid = xmlid_map.get(action_type)
        return self.env.ref(xmlid, raise_if_not_found=False) if xmlid else False

    def _resolve_recipient_partners(self, picking):
        """Return the recipient ``res.partner`` recordset for this config.

        Combines configured recipient users, members of recipient groups,
        and the GRN creator (when ``notify_creator`` is set).
        """
        self.ensure_one()
        Users = self.env['res.users']
        users = self.recipient_user_ids
        if self.recipient_group_ids:
            users |= Users.search([
                ('groups_id', 'in', self.recipient_group_ids.ids),
                ('share', '=', False),
                ('active', '=', True),
            ])
        if self.notify_creator and picking.create_uid:
            users |= picking.create_uid
        return users.partner_id

    def _resolve_approver_users(self):
        """Return the configured approver ``res.users`` recordset.

        Combines users in :attr:`approver_user_ids` and members of every
        group in :attr:`approver_group_ids`.
        """
        self.ensure_one()
        users = self.approver_user_ids
        if self.approver_group_ids:
            users |= self.env['res.users'].search([
                ('groups_id', 'in', self.approver_group_ids.ids),
                ('share', '=', False),
                ('active', '=', True),
            ])
        return users
