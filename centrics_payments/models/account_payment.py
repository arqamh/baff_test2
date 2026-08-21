from odoo import fields, models, api, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class InheritAccountPayment(models.Model):
    _name = "account.payment"
    _inherit = ['account.payment', 'analytic.mixin']

    receipt_id = fields.Many2one('account.receipt.payment')
    main_bank_id = fields.Many2one('main.bank', string="Bank")
    branch_id = fields.Many2one('res.bank', string="Branch")
    partner_bank_account_id = fields.Many2one('res.partner.bank', string="Account No")
    cheque_no = fields.Char(string="Cheque No")
    cheque_date = fields.Date(string="Cheque Date")
    is_cheque_ac_payee = fields.Boolean(string="A/c Payee", default=False)
    reference_no = fields.Char(string="Reference No")
    deposited_date = fields.Date(string="Deposited Date")
    payment_method_name = fields.Char(string="Payment Method", related='payment_method_id.name')

    #Payment Details
    requested_approver_id = fields.Many2one('res.users', tracking=True)
    approved_by = fields.Many2one('res.users', tracking=True, string="Approve or Rejected By")
    approved_date = fields.Date(tracking=True, string="Approve or Rejected Date")
    approved_comment = fields.Char(tracking=True, string="Approve or Rejected comment")

    bill_ids = fields.Many2many('account.move', 'biil_payment_rel', 'bill_id', 'payment_id')
    custom_url = fields.Char()
    is_available_payment_approval = fields.Boolean(default=False)
    is_cheque_date_confirmed = fields.Boolean(default=False)
    amount_in_words = fields.Char(string="Amount in Words", compute='_get_amount_in_words')

    def _get_amount_in_words(self):
        """Get amount in words"""

        self.amount_in_words = str(self.currency_id.amount_to_text(self.amount))

    @api.onchange('amount', 'payment_type')
    def _onchange_is_available_payment_approval(self):
        """Check payment approval for vendors"""
        for payment in self:
            configuration = self.env['ir.config_parameter'].sudo().get_param('centrics_payments.account_payment_approval')
            configured_amount = self.env['ir.config_parameter'].sudo().get_param(
                'centrics_payments.payment_approval_amount')
            if payment.state == "draft" and payment.payment_type == 'outbound' and configuration and payment.amount > float(
                    configured_amount):
                payment.is_available_payment_approval = True
            else:
                payment.is_available_payment_approval = False

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        res = super(InheritAccountPayment, self)._prepare_move_line_default_vals(write_off_line_vals)
        if self.analytic_distribution:
            for line in res[:2]:
                line['analytic_distribution'] = self.analytic_distribution
        return res

    def action_send_for_approval_payment(self):
        """Action for approve the payment and open wizard"""
        model = self.env['ir.model'].search([('model', '=', request.params.get('model'))])
        return {
            'name': _('Send to Approval'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'payment.sendfor.approval.wizard',
            'target': 'new',
            'context': {'default_payment_id': self.id,
                        'default_model_id': model.id}
        }

    def action_approve_payment(self):
        """Action for approve the payment and open wizard"""
        if self.payment_method_name == 'Cheque':
            if not self.cheque_date or not self.cheque_no:
                raise ValidationError("Cheque date and cheque no are required")
            if not self.env.context.get('confirm_cheque_date') and self.cheque_date != fields.Date.today():
                return self.action_open_cheque_date_validations()

        model = self.env['ir.model'].search([('model', '=', request.params.get('model'))])
        return {
            'name': _('Approve'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'payment.approve.reject.comment.wizard',
            'target': 'new',
            'context': {'default_payment_id': self.id,
                        'default_model_id': model.id,
                        'default_action': 'approve',
                        }
        }

    def action_reject_payment(self):
        """Action for reject the payment and open wizard"""
        model = self.env['ir.model'].search([('model', '=', request.params.get('model'))])
        return {
            'name': _('Reject'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'payment.approve.reject.comment.wizard',
            'target': 'new',
            'context': {'default_payment_id': self.id,
                        'default_model_id': model.id,
                        'default_action': 'reject',
                        }
        }

    def button_open_bills(self):
        """Open bills"""
        action = {
            'name': _('Bills'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.bill_ids.ids)],
            'context': {'create': False},
        }

        return action

    def update_payments_approval_request(self, approver):
        """Update state and send email for approval"""
        template_id = self.env.ref('centrics_payments.mail_template_for_account_payment_approval')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web?login/#id=' + str(self.id) + '&view_type=form&model=account.payment'
        self.write({
            'custom_url': url,
            'state': 'waiting_approval',
            'is_payment_approved': True,
            'requested_approver_id': approver.id,
        })
        self.env['mail.template'].browse(template_id.id).send_mail(self.id, True)

    def action_approve_payments(self):
        """Post and ureconcile journal enries"""
        self.action_post()
        if self.bill_ids:
            """Reconciled"""
            domain = [('account_internal_type', '=', 'payable'), ('reconciled', '=', False)]
            payment_lines = self.line_ids.filtered_domain(domain)
            lines = self.bill_ids.line_ids
            for account in payment_lines.account_id:
                (payment_lines + lines) \
                    .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]).reconcile()

    def update_payments_with_approve(self, approver, comment):
        """Update state and send email for reject"""
        self.is_cheque_date_confirmed = True
        self.action_approve_payments()
        template_id = self.env.ref('centrics_payments.mail_template_for_account_payment_after_approval')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web?login/#id=' + str(self.id) + '&view_type=form&model=account.payment'
        self.write({
            'custom_url': url,
            'approved_by': approver.id,
            # 'state': 'approved',
            'approved_date': datetime.today().date(),
            'approved_comment': comment if comment else '',
        })
        self.env['mail.template'].browse(template_id.id).send_mail(self.id, True)

    def update_payment_with_reject(self, approver, comment):
        """Update state and send email for approval"""
        template_id = self.env.ref('centrics_payments.mail_template_for_account_payment_after_reject')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web?login/#id=' + str(self.id) + '&view_type=form&model=account.payment'
        self.write({
            'custom_url': url,
            'approved_by': approver.id,
            'state': 'reject',
            'approved_date': datetime.today().date(),
            'approved_comment': comment,
        })
        self.env['mail.template'].browse(template_id.id).send_mail(self.id, True)

    def button_action_post(self):
        """Override Action_post method"""
        if self.payment_method_name == 'Cheque':
            if not self.cheque_date or not self.cheque_no:
                raise ValidationError("Cheque date and cheque no are required")
            if self.cheque_date != fields.Date.today():
                return self.action_open_cheque_date_validations()
        else:
            return self.action_post()

    def action_open_cheque_date_validations(self):
        """Open wizard for confirme cheque date"""
        if self.cheque_date < fields.Date.today():
            date_type = "Previous Date "
        else:
            date_type = "Future Date "
        message = " Cheque Date is a %s. \n " \
                  "Do you want to continue payment with this cheque date :- %s ." % (
                      date_type, self.cheque_date.strftime("%d-%m-%Y"))
        return {
            'name': _('Confirmation'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'pdc.confirmation.wizard',
            'target': 'new',
            'context': {
                'default_account_payment_id': self.id,
                'default_message': message,
            }
        }