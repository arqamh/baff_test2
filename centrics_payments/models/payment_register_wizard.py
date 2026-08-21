from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def default_get(self, fields_list):
        """Override default get method and add bill ids from context"""
        res = super(AccountPaymentRegister, self).default_get(fields_list)
        if self._context.get('active_model') == 'account.move':
            bills = self.env['account.move'].browse(self._context.get('active_ids', []))
            if bills:
                res["bill_ids"] = [(6, 0, bills.ids)]
        return res

    main_bank_id = fields.Many2one('main.bank', string="Bank")
    branch_id = fields.Many2one('res.bank', string="Branch")
    cheque_no = fields.Char(string="Cheque No")
    cheque_date = fields.Date(string="Cheque Date")
    is_cheque_ac_payee = fields.Boolean(string="A/c Payee", default=False)
    partner_bank_account_id = fields.Many2one('res.partner.bank', string="Account No")
    payment_method_name = fields.Char(string="Payment Method", related='payment_method_line_id.name')
    reference_no = fields.Char(string="Reference No")
    deposited_date = fields.Date(string="Deposited Date")

    is_available_payment_approval = fields.Boolean(compute="_compute_is_available_payment_approval")
    approver_id = fields.Many2one('res.users', string="Select an Approver")
    bill_ids = fields.Many2many('account.move', 'biil_payment_wizards_rel', 'bill_id', 'payment_id')

    # check date validation
    is_cheque_date_not_today = fields.Boolean(default="false")
    cheque_date_warning = fields.Text()

    def _create_payment_vals_from_wizard(self):
        """Inherit function and add new values"""
        res = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard('batch_result')
        res.update({
            'main_bank_id': self.main_bank_id.id if self.main_bank_id else False,
            'branch_id': self.branch_id.id if self.branch_id else False,
            'cheque_no': self.cheque_no,
            'cheque_date': self.cheque_date,
            'is_cheque_ac_payee': self.is_cheque_ac_payee,
            'reference_no': self.reference_no,
            'deposited_date': self.deposited_date,
            'partner_bank_account_id': self.partner_bank_account_id.id if self.partner_bank_account_id else False,
        })
        return res

    @api.depends('amount', 'payment_type')
    def _compute_is_available_payment_approval(self):
        """Check payment approval for vendors"""
        for payment in self:
            configuration = self.env['ir.config_parameter'].sudo().get_param('centrics_payments.account_payment_approval')
            configured_amount = self.env['ir.config_parameter'].sudo().get_param(
                'centrics_payments.payment_approval_amount')
            if payment.payment_type == 'outbound' and configuration and payment.amount > float(configured_amount):
                payment.is_available_payment_approval = True
            else:
                payment.is_available_payment_approval = False

    def _create_payments(self, is_with_approve=False):
        """Replace Parent method and added new condition for check approver and remove reconcilation methods """
        self.ensure_one()
        batches = self._get_batches()
        edit_mode = self.can_edit_wizard and (len(batches[0]['lines']) == 1 or self.group_payment)
        to_process = []

        if edit_mode:
            payment_vals = self._create_payment_vals_from_wizard()
            to_process.append({
                'create_vals': payment_vals,
                'to_reconcile': batches[0]['lines'],
                'batch': batches[0],
            })
        else:
            # Don't group payments: Create one batch per move.
            if not self.group_payment:
                new_batches = []
                for batch_result in batches:
                    for line in batch_result['lines']:
                        new_batches.append({
                            **batch_result,
                            'lines': line,
                        })
                batches = new_batches

            for batch_result in batches:
                to_process.append({
                    'create_vals': self._create_payment_vals_from_batch(batch_result),
                    'to_reconcile': batch_result['lines'],
                    'batch': batch_result,
                })

        payments = self._init_payments(to_process, edit_mode=edit_mode)
        if not is_with_approve:  # added new conditions for check approver
            self._post_payments(to_process, edit_mode=edit_mode)
            self._reconcile_payments(to_process, edit_mode=edit_mode)
        return payments

    def action_send_for_approval(self):
        """action to send payment for approval"""
        # create account payment
        payments = self._create_payments(is_with_approve=True)
        # Send Emails
        payments.write({
            'bill_ids': [(6, 0, self.bill_ids.ids)],
        })
        payments.update_payments_approval_request(self.approver_id)
        if self._context.get('dont_redirect_to_payments'):
            return True

        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })

        return action

    @api.onchange('cheque_date')
    def _onchange_cheque_date_validation(self):
        """function will trigger when change the cheque date
            if check date is not equal to today display a warning message
        """

        if self.cheque_date and self.cheque_date != fields.Date.today():
            if self.cheque_date < fields.Date.today():
                date_type = "Previous Date "
            else:
                date_type = "Future Date "
            message = " Cheque Date is a %s. \n " \
                      "Do you want to continue payment with this cheque date :- %s ." % (
                          date_type, self.cheque_date.strftime("%d-%m-%Y"))
            self.is_cheque_date_not_today = True
            self.cheque_date_warning = message

        else:
            self.is_cheque_date_not_today = False
