import datetime

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request


class RegisterPaymentMulti(models.Model):
    _name = "account.receipt.payment"
    _description = 'Register Payment'

    name = fields.Char(string="Name")
    partner_id = fields.Many2one('res.partner', string="Partner")
    user_id = fields.Many2one('res.users', string='Sales Person', default=lambda self: self.env.user, required=True)
    receipt_date = fields.Date(string="Receipt Date", default=fields.Date.today)
    manual_receipt_no = fields.Char(string="Manual Receipt No")
    remark = fields.Char(string="Remark")
    total_amount = fields.Monetary(string="Total Amount")
    currency_id = fields.Many2one('res.currency', default=lambda x: x.env.company.currency_id, string="Currency")
    invoice_ids = fields.One2many('temp.account.move', 'line_id')
    cash_payment_ids = fields.One2many('account.payment', 'receipt_id', domain=[('payment_method_name', '=', 'Cash')])
    over_payment_ids = fields.One2many('account.payment', 'receipt_id', domain=[('payment_method_name', '=', 'Over Payment')])
    deposit_payment_ids = fields.One2many('account.payment', 'receipt_id', domain=[('payment_method_name', '=', 'Direct Deposit')])
    cheque_payment_ids = fields.One2many('pdc.wizard', 'receipt_id')
    # add new line field when migrate
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
                                             readonly=False, store=True,
                                             compute='_compute_payment_method_line_id',
                                             domain="[('id', 'in', available_payment_method_line_ids)]",
                                             help="Manual: Pay or Get paid by any method outside of Odoo.\n"
                                                  "Payment Acquirers: Each payment acquirer has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.\n"
                                                  "Check: Pay bills by check and print it from Odoo.\n"
                                                  "Batch Deposit: Collect several customer checks at once generating and submitting a batch deposit to your bank. Module account_batch_payment is necessary.\n"
                                                  "SEPA Credit Transfer: Pay in the SEPA zone by submitting a SEPA Credit Transfer file to your bank. Module account_sepa is necessary.\n"
                                                  "SEPA Direct Debit: Get paid in the SEPA zone thanks to a mandate your partner will have granted to you. Module account_sepa is necessary.\n")
    available_payment_method_line_ids = fields.Many2many('account.payment.method.line',
                                                         compute='_compute_payment_method_line_fields')
    hide_payment_method_line = fields.Boolean(
        compute='_compute_payment_method_line_fields',
        help="Technical field used to hide the payment method if the selected journal has only one available which is 'manual'")

    payment_method_name = fields.Char(string="Payment Method")

    # payment_method_id = fields.Many2one('account.payment.method', string='Payment Method', readonly=False, store=True,
    #                                     domain="[('id', 'in', available_payment_method_ids)]",
    #                                     help="Manual: Get paid by cash, check or any other method outside of Odoo.\n" \
    #                                          "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n" \
    #                                          "Check: Pay bill by check and print it from Odoo.\n" \
    #                                          "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo, you are suggested to reconcile the transaction with the batch deposit.To enable batch deposit, module account_batch_payment must be installed.\n" \
    #                                          "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. To enable sepa credit transfer, module account_sepa must be installed ")
    #
    # available_payment_method_ids = fields.Many2many('account.payment.method', compute='_compute_payment_method_fields')
    # hide_payment_method = fields.Boolean(compute='_compute_payment_method_fields', help="Technical field used to hide the payment method if the selected journal has only one available which is 'manual'")
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type',
                                    store=True, copy=False, compute='_compute_from_lines')
    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')], store=True, copy=False,
                                    compute='_compute_from_lines')
    journal_id = fields.Many2one('account.journal', store=True, readonly=False,
                                 domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash'))]")
    company_id = fields.Many2one('res.company', store=True, copy=False, default=lambda self: self.env.company)
    over_payment_amount = fields.Float(string="Over Payment Amount")

    main_bank_id = fields.Many2one('main.bank', string="Bank")
    branch_id = fields.Many2one('res.bank', string="Branch")
    partner_bank_account_id = fields.Many2one('res.partner.bank', string="Account No")
    cheque_no = fields.Char(string="Cheque No")
    cheque_date = fields.Date(string="Cheque Date")
    is_cheque_ac_payee = fields.Boolean(string="A/c Payee", default=False)

    reference_no = fields.Char(string="Reference No")
    deposited_date = fields.Date(string="Deposited Date")
    lock = fields.Boolean(string='Source')
    state = fields.Selection([('draft', 'Draft'),
                              ('waiting_approval', 'Waiting For Approval'),
                              ('approved', 'Approved'),
                              ('reject', 'Rejected'),
                              ('paid', 'Paid')], default='draft')
    custom_url = fields.Char()
    requested_approver_id = fields.Many2one('res.users')
    approved_by = fields.Many2one('res.users', string="Approve or Rejected By")
    approved_date = fields.Date(string="Approve or Rejected Date")
    approved_comment = fields.Char(string="Approve or Rejected comment")

    @api.model
    def create(self, vals):
        """Call for the relates Assert Request/Transfer sequence and get the number to create the form"""
        vals['name'] = self.env['ir.sequence'].next_by_code('account.receipt.payment') or _('New')
        result = super(RegisterPaymentMulti, self).create(vals)
        return result

    # @api.onchange('journal_id')
    # def _compute_payment_method_fields(self):
    #     """Setting default payment method when journal changes"""
    #     if self.payment_type == 'inbound':
    #         self.available_payment_method_ids = self.journal_id.inbound_payment_method_line_ids.payment_method_id
    #         if self.journal_id.inbound_payment_method_line_ids.payment_method_id and self.payment_method_id.id not in self.journal_id.inbound_payment_method_line_ids.payment_method_id.ids:
    #             self.payment_method_id = self.journal_id.inbound_payment_method_line_ids.payment_method_id[0].id
    #     else:
    #         self.available_payment_method_ids = self.journal_id.outbound_payment_method_line_ids.payment_method_id
    #         if self.journal_id.outbound_payment_method_line_ids.payment_method_id and self.payment_method_id.id not in self.journal_id.outbound_payment_method_line_ids.payment_method_id.ids:
    #             self.payment_method_id = self.journal_id.outbound_payment_method_line_ids.payment_method_id[0].id
    #     self.hide_payment_method = len(self.available_payment_method_ids) == 1 and \
    #                                self.available_payment_method_ids.code == 'manual'
    #  V15 Migrations
    @api.depends('journal_id')
    def _compute_payment_method_line_id(self):
        for wizard in self:
            available_payment_method_lines = wizard.journal_id._get_available_payment_method_lines(wizard.payment_type)

            # Select the first available one by default.
            if available_payment_method_lines:
                wizard.payment_method_line_id = available_payment_method_lines[0]._origin
            else:
                wizard.payment_method_line_id = False


    @api.depends('journal_id')
    def _compute_payment_method_line_fields(self):
        for wizard in self:
            wizard.available_payment_method_line_ids = wizard.journal_id._get_available_payment_method_lines(
                wizard.payment_type)
            if wizard.payment_method_line_id.id not in wizard.available_payment_method_line_ids.ids:
                # In some cases, we could be linked to a payment method line that has been unlinked from the journal.
                # In such cases, we want to show it on the payment.
                wizard.hide_payment_method_line = False
            else:
                wizard.hide_payment_method_line = len(wizard.available_payment_method_line_ids) == 1 \
                                                  and wizard.available_payment_method_line_ids.code == 'manual'
    #
    @api.onchange('payment_method_line_id')
    def onchange_payment_method_line_id(self):
        """set payment_method_name on onchange"""
        self.payment_method_name = self.payment_method_line_id.name

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """Load invoices for the partner if the record is not loaded"""
        if self.partner_id and not self.lock:
            missing_invoices = []
            invoices = self.env['account.move'].search([('partner_id', '=', self.partner_id.id),
                                                        ('amount_residual', '>', 0), ('state', '=', 'posted'),
                                                        ('move_type', '=', 'out_invoice' if self.payment_type == 'inbound' else 'in_invoice')])
            self.invoice_ids = None
            for missing_invoice in invoices:
                missing_invoices.append((0, 0, {
                    'invoice_id': missing_invoice.id,
                    'invoice_date': missing_invoice.invoice_date,
                    'invoice_age': (datetime.datetime.now().date() - missing_invoice.invoice_date).days,
                    'invoice_total': missing_invoice.amount_total,
                    'invoice_actual_due': missing_invoice.amount_residual,
                    'invoice_current_due': missing_invoice.amount_residual,
                    'invoice_paying_amount': 0,
                    'currency_id': missing_invoice.currency_id.id,
                }))
            self.invoice_ids = missing_invoices

    def _default_invoice_lines(self, invoices):
        """need to return payment lines by adding given credit payment data"""
        payment_lines = []
        for invoice in invoices:
            payment_lines.append((0, 0, {
                'invoice_id': invoice.id,
                'invoice_date': invoice.invoice_date,
                'invoice_age': (datetime.datetime.now().date() - invoice.invoice_date).days,
                'invoice_total': invoice.amount_total,
                'invoice_actual_due': invoice.amount_residual,
                'invoice_current_due': invoice.amount_residual,
                'invoice_paying_amount': invoice.amount_residual,
                'currency_id': invoice.currency_id,
            }))
        return payment_lines

    def close_receipt(self):
        """Close Receipt"""
        self.write({
            "state": "paid"
        })

    def create_payments(self):
        """Create a payment when add to payments button is clicked"""
        if self.payment_method_name in ['Cheque', 'Cash', 'Direct Deposit']:
            if not self.invoice_ids.filtered(lambda x: x.is_ticked == True):
                raise UserError("Please select at least on Invoice to make a payment.")
            if self.invoice_ids.filtered(lambda x: x.is_ticked == True and x.invoice_paying_amount <= 0):
                raise UserError("The payment should be greater than 0.")
        # Creating Overpayments
        if self.payment_method_name == 'Over Payment':
            payment = self.env['account.payment'].create({
                "payment_type": self.payment_type,
                "partner_type": self.partner_type,
                "partner_id": self.partner_id.id,
                "payment_method_line_id": self.payment_method_line_id.id,
                "amount": self.over_payment_amount,
                "receipt_id": self.id,
                "journal_id": self.journal_id.id,
                "currency_id": self.currency_id.id,
                "user_id": self.user_id.id,
            })
            # payment.action_post()
        # Creating Cheque Payments
        elif self.payment_method_name == 'Cheque':
            invoice_list = []
            total_amount = 0.00
            invoice_names = []
            for invoice in self.invoice_ids.filtered(lambda x: x.is_ticked == True):
                total_amount += invoice.invoice_paying_amount
                invoice_names.append(invoice.invoice_id.name)
                invoice_list.append((0, 0, {'invoice_id': invoice.invoice_id.id, 'invoice_paying_amount': invoice.invoice_paying_amount} ))
            payment = self.env['pdc.wizard'].create({
                "payment_type": "receive_money" if self.payment_type == 'inbound' else "send_money",
                "partner_id": self.partner_id.id,
                "receipt_id": self.id,
                "payment_amount": total_amount,
                "journal_id": self.journal_id.id,
                "invoice_id_lines": invoice_list,
                'memo': ', '.join(invoice_names),
                "reference": self.cheque_no,
                "payment_date": self.receipt_date,
                "due_date": self.receipt_date,
                "bank_id": self.branch_id.id,
                "main_bank_id": self.main_bank_id.id,
                "partner_bank_account_id": self.partner_bank_account_id.id,
            })
                # payment.action_register()
                # payment.action_deposited()
            invoice.write({
                    # "invoice_actual_due": invoice.invoice_id.amount_residual,
                    "invoice_paying_amount": 0,
                    "is_ticked": False,
            })
        # Creating all other payment methods
        else:
            for invoice in self.invoice_ids.filtered(lambda x: x.is_ticked == True):
                payment = self.env['account.payment'].create({
                    "payment_type": self.payment_type,
                    "partner_type": self.partner_type,
                    "partner_id": self.partner_id.id,
                    "payment_method_line_id": self.payment_method_line_id.id,
                    "amount": invoice.invoice_paying_amount,
                    "receipt_id": self.id,
                    "bill_ids": [(6,0, [invoice.invoice_id.id])],
                    "journal_id": self.journal_id.id,
                    "currency_id": invoice.paying_currency_id.id,
                    "main_bank_id": self.main_bank_id.id,
                    "partner_bank_account_id": self.partner_bank_account_id.id,
                    "reference_no": self.reference_no,
                    "deposited_date": self.deposited_date,
                    "branch_id": self.branch_id.id,
                    "user_id": self.user_id.id,
                })
                # payment.action_post()
                # account_move_lines_to_reconcile = self.env['account.move.line']
                # for line in invoice.invoice_id.line_ids + payment.line_ids:
                #     if self.payment_type == 'inbound':
                #         if line.account_id.internal_type == 'receivable' and not line.reconciled:
                #             account_move_lines_to_reconcile |= line
                #     else:
                #         if line.account_id.internal_type == 'payable' and not line.reconciled:
                #             account_move_lines_to_reconcile |= line
                # account_move_lines_to_reconcile.reconcile()
                invoice.write({
                    # "invoice_actual_due": invoice.invoice_id.amount_residual,
                    "invoice_paying_amount": 0,
                    "is_ticked": False,
                })

    def action_send_for_approval_payment(self):
        """Action for approve the payment and open wizard"""
        model = self.env['ir.model'].search([('model', '=', request.params.get('model'))])
        return {
            'name': _('Send to Approval'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'payment.sendfor.approval.wizard',
            'target': 'new',
            'context': {'default_bulk_payment_id': self.id,
                        'default_model_id': model.id}
        }

    def update_payments_approval_request(self, approver):
        """Update state and send email for approval"""
        template_id = self.env.ref('centrics_payments.mail_template_for_bulk_payment_approval')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web?login/#id=' + str(self.id) + '&view_type=form&model=account.receipt.payment'
        self.write({
            'custom_url': url,
            'state': 'waiting_approval',
            'requested_approver_id': approver.id,
        })
        self.env['mail.template'].browse(template_id.id).send_mail(self.id, True)

    def action_approve_payment(self):
        """Action for approve the payment and open wizard"""

        model = self.env['ir.model'].search([('model', '=', request.params.get('model'))])
        return {
            'name': _('Approve'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'payment.approve.reject.comment.wizard',
            'target': 'new',
            'context': {'default_bulk_payment_id': self.id,
                        'default_model_id': model.id,
                        'default_action': 'approve',
                        }
        }

    def update_payments_with_approve(self, approver, comment):
        """Update state and send email for reject"""
        template_id = self.env.ref('centrics_payments.mail_template_for_bulk_payment_after_approval')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web?login/#id=' + str(self.id) + '&view_type=form&model=account.receipt.payment'
        self.write({
            'custom_url': url,
            'approved_by': approver.id,
            'state': 'approved',
            'approved_date': datetime.datetime.today().date(),
            'approved_comment': comment if comment else '',
        })
        for pdc in self.cheque_payment_ids:
            pdc.triggered_approval = True
            pdc.state = "approved"
        for cash_payment in self.cash_payment_ids:
            cash_payment.is_available_payment_approval = False
        for over_payment in self.over_payment_ids:
            over_payment.is_available_payment_approval = False
            self.action_post_payments(over_payment)
        self.env['mail.template'].browse(template_id.id).send_mail(self.id, True)

    def action_post_payments(self, payment):
        """Post and reconciled generated payments"""
        payment.action_post()
        account_move_lines_to_reconcile = self.env['account.move.line']
        for line in payment.bill_ids.line_ids + payment.line_ids:
            if self.payment_type == 'inbound':
                if line.account_id.internal_type == 'receivable' and not line.reconciled:
                    account_move_lines_to_reconcile |= line
            else:
                if line.account_id.internal_type == 'payable' and not line.reconciled:
                    account_move_lines_to_reconcile |= line
        account_move_lines_to_reconcile.reconcile()

    def action_reject_payment(self):
        """Action for reject the payment and open wizard"""
        model = self.env['ir.model'].search([('model', '=', request.params.get('model'))])
        return {
            'name': _('Reject'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'payment.approve.reject.comment.wizard',
            'target': 'new',
            'context': {'default_bulk_payment_id': self.id,
                        'default_model_id': model.id,
                        'default_action': 'reject',
                        }
        }

    def update_payment_with_reject(self, approver, comment):
        """Update state and send email for approval"""
        template_id = self.env.ref('centrics_payments.mail_template_for_bulk_payment_after_reject')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web?login/#id=' + str(self.id) + '&view_type=form&model=account.receipt.payment'
        self.write({
            'custom_url': url,
            'approved_by': approver.id,
            'state': 'reject',
            'approved_date': datetime.datetime.today().date(),
            'approved_comment': comment,
        })
        self.env['mail.template'].browse(template_id.id).send_mail(self.id, True)


class TempAccountMove(models.Model):
    _name = "temp.account.move"
    _description = "Temp Account Move"

    line_id = fields.Many2one('account.receipt.payment')
    is_ticked = fields.Boolean(default=False)
    invoice_id = fields.Many2one('account.move', string="Invoice No")
    invoice_date = fields.Date(string="Invoice Date")
    invoice_age = fields.Integer(string="Invoice Age")
    invoice_total = fields.Monetary(string="Invoice Total")
    invoice_actual_due = fields.Monetary(string="Invoice Actual Due")
    invoice_current_due = fields.Monetary(string="Invoice Current Due")
    invoice_paying_amount = fields.Monetary(string="Paying Amount", currency_field='paying_currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda x: x.env.company.currency_id, string="Currency")
    paying_currency_id = fields.Many2one('res.currency', default=lambda x: x.env.company.currency_id, string="Currency")

    # @api.onchange('paying_currency_id')
    # def onchange_paying_currency_id(self):
    #     """Calculate paymen"""
    #     self.invoice_paying_amount = self.currency_id._convert(self.invoice_current_due, self.paying_currency_id, self.line_id.company_id, self.line_id.receipt_date, round=True)


