# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


APPROVAL_STATE_VALUES = ('waiting_approval', 'approved', 'rejected')
APPROVAL_HOLD_STATES = ('waiting_approval', 'rejected')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    state = fields.Selection(
        selection_add=[
            ('waiting_approval', 'Waiting Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('done',),
            ('cancel',),
        ],
        ondelete={
            'waiting_approval': 'set draft',
            'approved': 'set draft',
            'rejected': 'set draft',
        })

    is_grn = fields.Boolean(
        string='Is GRN', compute='_compute_is_grn', store=True,
        help='Technical: True when this transfer is an incoming transfer '
             'subject to the GRN approval workflow.')

    grn_approver_ids = fields.Many2many(
        'res.users', 'grn_picking_approver_rel',
        'picking_id', 'user_id',
        string='Configured Approvers', copy=False,
        help='Users allowed to approve or reject this GRN, snapshot at '
             'submission time from the matching configuration.')

    submitted_by = fields.Many2one(
        'res.users', string='Submitted By', copy=False, readonly=True)
    submitted_date = fields.Datetime(
        string='Submitted On', copy=False, readonly=True)

    approved_by = fields.Many2one(
        'res.users', string='Approved By', copy=False, readonly=True)
    approval_date = fields.Datetime(
        string='Approved On', copy=False, readonly=True)
    approval_remarks = fields.Text(
        string='Approval Remarks', copy=False, readonly=True)

    rejected_by = fields.Many2one(
        'res.users', string='Rejected By', copy=False, readonly=True)
    rejection_date = fields.Datetime(
        string='Rejected On', copy=False, readonly=True)
    rejection_reason = fields.Text(
        string='Rejection Reason', copy=False, readonly=True)

    approval_log_ids = fields.One2many(
        'grn.approval.log', 'picking_id', string='Approval History',
        copy=False, readonly=True)

    show_grn_submit = fields.Boolean(compute='_compute_grn_buttons')
    show_grn_approve_reject = fields.Boolean(compute='_compute_grn_buttons')
    show_grn_reset = fields.Boolean(compute='_compute_grn_buttons')

    @api.depends('picking_type_id', 'picking_type_id.code')
    def _compute_is_grn(self):
        for rec in self:
            rec.is_grn = rec.picking_type_id.code == 'incoming'

    @api.depends('state', 'is_grn', 'grn_approver_ids')
    def _compute_grn_buttons(self):
        uid = self.env.uid
        is_admin = self.env.user.has_group(
            'grn_approval_workflow.grn_approval_workflow_group_admin')
        fallback_approver = self.env.user.has_group(
            'grn_approval_workflow.grn_approval_workflow_group_approver')
        for rec in self:
            rec.show_grn_submit = (
                rec.is_grn
                and rec.state not in (
                    'waiting_approval', 'approved', 'rejected', 'done', 'cancel')
            )
            if rec.state == 'waiting_approval':
                if rec.grn_approver_ids:
                    can_act = uid in rec.grn_approver_ids.ids
                else:
                    can_act = fallback_approver
                rec.show_grn_approve_reject = can_act
            else:
                rec.show_grn_approve_reject = False
            rec.show_grn_reset = (
                rec.is_grn
                and rec.state == 'rejected'
                and (is_admin or uid == rec.create_uid.id)
            )

    # ------------------------------------------------------------------
    # State preservation: keep approval values intact while moves churn
    # ------------------------------------------------------------------
    def _compute_state(self):
        """Preserve GRN approval states across move-driven recomputation.

        * ``waiting_approval`` and ``rejected`` are sticky — they stay until
          an explicit workflow action resets them.
        * ``approved`` stays until the underlying moves are all ``done``,
          at which point the picking naturally transitions to ``done``.
        * Context flag ``grn_skip_approval_hold`` bypasses the sticky logic
          (used by reset-to-draft to let state recompute from moves).
        """
        if self.env.context.get('grn_skip_approval_hold'):
            return super()._compute_state()

        held = self.filtered(lambda p: p.state in APPROVAL_HOLD_STATES)
        approved = self.filtered(lambda p: p.state == 'approved')
        rest = self - held - approved

        super(StockPicking, rest)._compute_state()

        if approved:
            super(StockPicking, approved)._compute_state()
            for picking in approved:
                if picking.state != 'done':
                    picking.state = 'approved'

    @api.depends('state')
    def _compute_show_validate(self):
        """Keep the native Validate button visible for approved GRNs.

        The native compute hides Validate for any state outside
        ``(draft, waiting, confirmed, assigned)``, which would suppress it
        the moment a GRN transitions to ``approved``.
        """
        super()._compute_show_validate()
        for picking in self:
            if picking.is_grn and picking.state == 'approved' and picking.is_locked:
                picking.show_validate = True

    # ------------------------------------------------------------------
    # Configuration resolution
    # ------------------------------------------------------------------
    def _find_approval_config(self, action_type):
        self.ensure_one()
        Config = self.env['grn.approval.config'].sudo()
        domain = [
            ('action_type', '=', action_type),
            ('active', '=', True),
            ('company_id', '=', self.company_id.id),
        ]
        configs = Config.search(domain)
        if not configs:
            return Config
        specific = configs.filtered(
            lambda c: self.picking_type_id in c.picking_type_ids)
        if specific:
            return specific[:1]
        generic = configs.filtered(lambda c: not c.picking_type_ids)
        return generic[:1] if generic else Config

    def _get_fallback_approver_users(self):
        group = self.env.ref(
            'grn_approval_workflow.grn_approval_workflow_group_approver',
            raise_if_not_found=False)
        if not group:
            return self.env['res.users']
        return self.env['res.users'].search([
            ('groups_id', 'in', group.ids),
            ('share', '=', False),
            ('active', '=', True),
        ])

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_grn_submit_for_approval(self):
        """Open the Submit wizard pre-populated with the resolved approvers.

        The user can remove any approvers who are not required before
        confirming. The actual state transition happens in
        :meth:`_perform_grn_submit`, called from the wizard.
        """
        self.ensure_one()
        if not self.is_grn:
            raise UserError(_(
                "Only incoming transfers (GRNs) use the approval workflow."))
        if self.state in APPROVAL_STATE_VALUES + ('done', 'cancel'):
            raise UserError(_(
                "GRN %s cannot be submitted for approval from its current state.",
                self.name))
        config = self._find_approval_config('submit')
        approvers = config._resolve_approver_users() if config else self.env['res.users']
        if not approvers:
            approvers = self._get_fallback_approver_users()
        if not approvers:
            raise UserError(_(
                "No approvers are configured. Please set up the GRN "
                "Approval Configuration or add members to the GRN "
                "Approver group."))
        return {
            'name': _('Submit for Approval'),
            'type': 'ir.actions.act_window',
            'res_model': 'grn.submit.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_approver_ids': [(6, 0, approvers.ids)],
            },
        }

    def _perform_grn_submit(self, approvers):
        """Apply the submission with the (possibly edited) approver list."""
        self.ensure_one()
        if not approvers:
            raise UserError(_(
                "At least one approver is required to submit this GRN."))
        if self.state in APPROVAL_STATE_VALUES + ('done', 'cancel'):
            raise UserError(_(
                "GRN %s cannot be submitted for approval from its current state.",
                self.name))
        self.write({
            'state': 'waiting_approval',
            'grn_approver_ids': [(6, 0, approvers.ids)],
            'submitted_by': self.env.uid,
            'submitted_date': fields.Datetime.now(),
        })
        self._log_approval_event('submit')
        self.message_post(body=_(
            "GRN submitted for approval. Pending approver(s): %s",
            ', '.join(approvers.mapped('name'))))
        self._send_grn_notification('submit', extra_partners=approvers.partner_id)
        return True

    def action_grn_approve(self):
        for rec in self:
            rec._check_approval_rights('approve')
            rec.write({
                'state': 'approved',
                'approved_by': self.env.uid,
                'approval_date': fields.Datetime.now(),
            })
            rec._log_approval_event('approve')
            rec.message_post(body=_("GRN approved by %s.", self.env.user.name))
            rec._send_grn_notification('approve')
        return True

    def action_grn_open_reject_wizard(self):
        self.ensure_one()
        self._check_approval_rights('reject')
        return {
            'name': _('Reject GRN'),
            'type': 'ir.actions.act_window',
            'res_model': 'grn.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id},
        }

    def action_grn_reject(self, reason, remarks=None):
        if not reason or not reason.strip():
            raise UserError(_("A rejection reason is required."))
        for rec in self:
            rec._check_approval_rights('reject')
            rec.write({
                'state': 'rejected',
                'rejected_by': self.env.uid,
                'rejection_date': fields.Datetime.now(),
                'rejection_reason': reason,
                'approval_remarks': remarks or False,
            })
            rec._log_approval_event('reject', reason=reason, remarks=remarks)
            rec.message_post(body=_(
                "GRN rejected by %(user)s.<br/>Reason: %(reason)s",
                user=self.env.user.name, reason=reason))
            rec._send_grn_notification('reject')
        return True

    def action_grn_reset_to_draft(self):
        """Take a rejected GRN back into the standard stock flow.

        We don't write ``state='draft'`` directly — the compute will resolve
        the natural state from the underlying moves (assigned / confirmed /
        waiting / draft).
        """
        for rec in self:
            if not rec.is_grn:
                continue
            if rec.state != 'rejected':
                raise UserError(_(
                    "Only rejected GRNs can be reset to draft."))
            rec.write({
                'grn_approver_ids': [(5, 0)],
                'submitted_by': False,
                'submitted_date': False,
                'rejected_by': False,
                'rejection_date': False,
                'rejection_reason': False,
                'approval_remarks': False,
            })
            # Force the natural state recomputation from moves.
            rec.with_context(grn_skip_approval_hold=True)._compute_state()
            rec.message_post(body=_("GRN reset for re-submission."))
        return True

    def _check_approval_rights(self, action):
        self.ensure_one()
        if not self.is_grn:
            raise UserError(_(
                "Only incoming transfers (GRNs) use the approval workflow."))
        if self.state != 'waiting_approval':
            raise UserError(_(
                "GRN %s is not waiting for approval.", self.name))
        uid = self.env.uid
        if self.grn_approver_ids:
            if uid not in self.grn_approver_ids.ids:
                raise UserError(_(
                    "You are not configured as an approver for this GRN."))
        else:
            if not self.env.user.has_group(
                    'grn_approval_workflow.grn_approval_workflow_group_approver'):
                raise UserError(_(
                    "You are not allowed to %s this GRN.", action))

    # ------------------------------------------------------------------
    # Validation gate
    # ------------------------------------------------------------------
    def button_validate(self):
        for rec in self:
            if rec.is_grn and rec.state not in ('approved', 'done'):
                raise UserError(_(
                    "GRN %s must be approved before it can be validated.",
                    rec.name))
        return super().button_validate()

    # ------------------------------------------------------------------
    # Logging and notifications
    # ------------------------------------------------------------------
    def _log_approval_event(self, action, reason=None, remarks=None):
        self.ensure_one()
        self.env['grn.approval.log'].sudo().create({
            'picking_id': self.id,
            'action': action,
            'user_id': self.env.uid,
            'event_date': fields.Datetime.now(),
            'reason': reason or False,
            'remarks': remarks or False,
        })

    def _send_grn_notification(self, action_type, extra_partners=None):
        self.ensure_one()
        config = self._find_approval_config(action_type)
        template = config.template_id if config else False
        if not template:
            template = self.env['grn.approval.config']._get_default_template(action_type)
        if not template:
            _logger.warning(
                "GRN approval: no email template found for action %s on picking %s",
                action_type, self.name)
            return False

        partners = self.env['res.partner']
        if config:
            partners |= config._resolve_recipient_partners(self)
        if action_type in ('approve', 'reject') and self.create_uid:
            partners |= self.create_uid.partner_id
        if extra_partners:
            partners |= extra_partners
        partners = partners.filtered(lambda p: p.email)

        if not partners:
            _logger.info(
                "GRN approval: no recipients resolved for action %s on %s",
                action_type, self.name)
            return False

        ctx = {
            'recipient_partner_ids': partners.ids,
            'grn_action': action_type,
        }
        return template.with_context(**ctx).send_mail(
            self.id, force_send=False,
            email_values={
                'recipient_ids': [(6, 0, partners.ids)],
            })
