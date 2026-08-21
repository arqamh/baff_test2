# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import models, fields, _, api
from datetime import datetime
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_order_approval_line_ids = fields.One2many('purchase.order.approval.lines', 'purchase_order_id')
    hide_approve_reject_button = fields.Boolean(string="Hide Approve Button", compute='_compute_hide_approve_reject_button')
    requested_user = fields.Many2one('res.users', string="Pending Approver", compute='_compute_requested_user', store=True)

    @api.depends('purchase_order_approval_line_ids.state')
    def _compute_requested_user(self):
        """function to compute the requested user for each purchase order."""
        for order in self:
            requested_user = False
            for line in order.purchase_order_approval_line_ids.filtered(lambda x: x.state == 'requested'):
                requested_user = line.user_id.id
                break
            order.requested_user = requested_user

    def _compute_hide_approve_reject_button(self):
        """function to decide whether to hide approve & reject buttons"""
        for record in self:
            if record.purchase_order_approval_line_ids.filtered(lambda x: x.user_id.id == self._uid and x.state == 'requested'):
                record.hide_approve_reject_button = False
            else:
                record.hide_approve_reject_button = True

    def update_approvers(self):
        """function to update approvers"""
        vals = []
        count = 1
        for line in self.purchase_order_approval_line_ids.filtered(lambda x: x.state not in ['approved', 'rejected']):
            vals.append((0, 0, {
                'sequence': count,
                'user_id': line.user_id.id,
                'po_approve_line_id': line.id,
            }))
            count += 1
        return {
            'name': _('Update Approvers'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'purchase.order.approvers.wizard',
            'target': 'new',
            'context': {'default_purchase_order_approver_line_ids': vals, 'default_type': 'update'}
        }

    def send_for_approval(self):
        """Loads the wizard to send for approval"""
        amount = self.currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id,
                                           self.date_order or fields.Date.today())
        approval_line = self.company_id.purchase_order_config_approval_line_ids.filtered(
            lambda x: x.amount_from <= amount <= x.amount_to)
        if not approval_line:
            raise UserError("Please define an approval line for the purchase order value.")
        vals = []
        count = 1
        for user in approval_line.user_ids:
            vals.append((0, 0, {
                'sequence': count,
                'user_id': user.id,
            }))
            count += 1
        return {
            'name': _('Send For Approval'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'purchase.order.approvers.wizard',
            'target': 'new',
            'context': {'default_purchase_order_approver_line_ids': vals}
        }

    def _get_email_message(self):
        """
        @private - get email message for approves
        """
        return Markup(f"""
        There is a pending purchase order for your approval
        <br/>
        <br/>
        <br/>
        <table class='table table-sm table-striped'>
            <tr class='table-secondary'><th colspan='2' class='text-center'>Purchase Order Details</th></tr>
            <tr>
                <th>Purchase Order</th>
                <td>{self.name}</td>
            </tr>
            <tr>
                <th>Division</th>
                <td>{self.company_id.name}</td>
            </tr>
        </table>
        """)

    def send_to_next_approver(self):
        """This function automatically sets next available approver."""
        if self.state in ['draft', 'sent']:
            self.write({
                'state': 'to approve'
            })
        next_approvers = self.purchase_order_approval_line_ids.filtered(lambda x: x.state == 'pending')
        if next_approvers:
            next_approvers[0].write({
                'state': 'requested',
                'approval_request_datetime': datetime.now(),
            })
            template_id = self.env.ref(
                'centrics_purchase_multi_user_approval.centrics_purchase_multi_user_approval_request_for_approval_mail_template')
            msg = self._get_email_message()
            self.with_context(mail_body={}).send_email_purchase(self.id, self._context.get('active_model'),
                                                                "Request for Approval", next_approvers[0].user_id,
                                                                template_id, msg)

    def button_reject(self):
        """New function to reject POs."""
        approver_line = self.purchase_order_approval_line_ids.filtered(
            lambda x: x.user_id.id == self._uid and x.state == 'requested')
        if not approver_line:
            raise UserError("You Don't have access to approve.")
        approver_line.write({
            'state': 'rejected',
            'status_updated_datetime': datetime.now(),
        })
        self.button_cancel()
        template_id = self.env.ref(
            'centrics_purchase_multi_user_approval.centrics_purchase_multi_user_approval_reject_or_approve_template')
        msg = 'The following purchase order is rejected by %s' % self.env['res.users'].browse(self._uid).name
        self.with_context(mail_body={}).send_email_purchase(self.id, self._context.get('active_model'), "Rejected",
                                                            self.create_uid, template_id, msg)

    def button_approve(self):
        """This is a core function which is completely overidden"""
        approver_line = self.purchase_order_approval_line_ids.filtered(
            lambda x: x.user_id.id == self._uid and x.state == 'requested')
        if not approver_line:
            raise UserError("You Don't have access to approve.")
        approver_line.write({
            'state': 'approved',
            'status_updated_datetime': datetime.now(),
        })
        next_approver_line = self.purchase_order_approval_line_ids.filtered(lambda x: x.state == 'pending')
        if next_approver_line:
            self.send_to_next_approver()
        else:
            template_id = self.env.ref(
                'centrics_purchase_multi_user_approval.centrics_purchase_multi_user_approval_reject_or_approve_template')
            msg = 'The following purchase order is approved by %s' % self.env['res.users'].browse(self._uid).name
            self.with_context(mail_body={}).send_email_purchase(self.id, self._context.get('active_model'), "Approved",
                                                                self.create_uid, template_id, msg)
            self.button_confirm()

    def button_confirm(self):
        """Inheriting confirm button inorder to add to confirm to approve state POs."""
        for order in self:
            if order.state not in ['draft', 'sent', 'to approve', 'approved']:
                continue
            order.order_line._validate_analytic_distribution()
            order._add_supplier_to_product()
            order.write({'state': 'purchase', 'date_approve': fields.Datetime.now()})
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
            order._create_picking()
        return True

    def send_email_purchase(self, record, model, subject, users, template_id, msg):
        """Common function to send email. Parameters contains all required date for the mail template"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = '%s/web?login/#id=%s&view_type=form&model=%s' % (base_url, record, model)
        context = self.env.context.get('mail_body')
        context['mail_to'] = ','.join([str(x.partner_id.id) for x in users])
        context['custom_url'] = url
        context['subject'] = subject
        context['msg_type'] = msg
        self.env['mail.template'].sudo().browse(template_id.id).with_context(context).send_mail(self.id, True)


class PurchaseOrderApprovalLines(models.Model):
    _name = 'purchase.order.approval.lines'
    _description = "Purchase Order Approval Lines"
    _order = 'sequence'

    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order")
    sequence = fields.Integer(string="Sequence", default=1)
    user_id = fields.Many2one('res.users', string="Users")
    state = fields.Selection(
        [('pending', 'Pending'), ('requested', 'Requested'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending')
    approval_request_datetime = fields.Datetime(string="Approval Request Date")
    status_updated_datetime = fields.Datetime(string="Last Status Updated Date")
    show_signature = fields.Boolean(string="Show Signature")
