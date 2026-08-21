import calendar
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.http import request

class PettyCashRelease(models.Model):
    """
    Petty cash Release Handling class
    """
    _name = "petty.cash.release"
    _description = "IOU Request"
    _order = "create_date desc"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char("Number", copy=False, default=lambda self: _('New'))
    release_date = fields.Datetime(string="Requested Date",copy=False, default=fields.Datetime.now)
    petty_cash_id = fields.Many2one("petty.cash", string="Petty Cash Drawer", required=True)
    reimbursement_id = fields.Many2one("petty.cash.out", string="Reimbursement")
    employee_id = fields.Many2one('hr.employee', string="Requested Employee", required=True)
    user_id = fields.Many2one("res.users", string="Responsible Person", copy=False, default=lambda self: self.env.user, required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", required=True, readonly=False,
                                  string='Currency')
    requested_amount = fields.Float(string="Requested Amount", copy=False, default=0.00,  tracking=True, store=True, required=True)
    released_amount = fields.Float(string="Approved Amount", copy=False, default=0.00,  tracking=True, store=True, required=True)
    expensed_amount = fields.Float(string="Expensed Amount", compute="_compute_balanced_amount", copy=False, default=0.00, tracking=True, store=True)
    balanced_amount = fields.Float(string="Balanced Amount", compute="_compute_balanced_amount", store=True)
    reason = fields.Many2one('petty.cash.reason',)
    approved_by = fields.Many2one("res.users", string="Approved/Rejected User", copy=False, readonly=True)
    approver_comment = fields.Char('Approved/Rejected Reason', copy=False, tracking=True)
    approved_date = fields.Datetime(string="Approved/Rejected Date", copy=False, tracking=True)
    move_id = fields.Many2many('account.move', 'cash_release_move_rel', 'cash_out_id', 'move_id', string="Journal Entries",
                               copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('awaiting_approval', 'Awaiting Approval'),
        ('approved', 'Approved'),
        ('reject', 'Rejected'),
        ('released', 'Cash Issued'),
        ('open', 'Open'),
        ('complete', 'Completed')], string="Status", default="draft", copy=False, tracking=True)

    remarks = fields.Text()
    comment = fields.Text()
    petty_cash_line_id = fields.Many2one('petty.cash.line')
    expenses_line = fields.One2many('petty.cash.release.line', 'cash_release_id', string='Expenses line')

    is_wizard = fields.Boolean(default=False)
    checked_by = fields.Many2one('res.users', string="Checked By", tracking=True)
    cheque_no = fields.Char()
    cheque_date = fields.Date(string="Cheque Date")
    is_cheque_ac_payee = fields.Boolean(string="A/c Payee", default=False)
    is_vendor_bill_statement = fields.Boolean(string="Vendor Bill Statement")
    vendor_bills = fields.One2many('petty.cash.vendor.bills', 'iou_request_id', string="Vendor Bills")
    is_price_change = fields.Boolean(default=False)
    price_change_note = fields.Char('Reason for price change')

    @api.model_create_multi
    def create(self, values):
        """Override create method and add a sequence"""
        results = super(PettyCashRelease, self).create(values)
        for result in results:
            if result.name == 'New':
                result.name = result.petty_cash_id.iou_sequence_id.next_by_id()

            # Create a log for relevant petty cash log entries after finishing
            cash_line_id = self.env['petty.cash.line'].create({
                'name': result.name,
                'petty_cash_id': result.petty_cash_id.id,
                'from_acc': result.petty_cash_id.journal_id.default_account_id.id,
                # 'to_acc': self.employee_id.address_home_id.property_account_payable_id.id,
                'reason': result.reason.name if result.reason else '',
                'amount': result.released_amount,
                'user_id': result.user_id.id,
                'employee_id': result.employee_id.id,
                'approved_by': False,
                'cash_release_id': result.id,
            })
            result.petty_cash_line_id = cash_line_id.id
        return results

    def get_expense_amount_for_drawer_log(self):
        """calculate expenses amount """
        expenses_amount = 0.00
        if self.state == 'complete':
            expenses_amount = self.expensed_amount - self.reimbursement_id.iou_balance if self.reimbursement_id else self.expensed_amount
        else:
            expenses_amount = self.released_amount

        return expenses_amount

    def write(self, vals):
        """Override Write method"""
        res = super(PettyCashRelease, self).write(vals)
        if res:
            #   Update log in petty cash
            self.petty_cash_line_id.write({
                'to_acc': self.employee_id.sudo().address_home_id.property_account_receivable_id.id if self.employee_id.sudo().address_home_id else False,
                'reason': self.reason.name if self.reason else '',
                'amount': self.get_expense_amount_for_drawer_log(),
                'user_id': self.user_id.id,
                'approved_by': self.approved_by.id if self.approved_by else False,
            })
        return res

    def action_add_vendor_bills_to_iou(self):
        """action for open wizard for select vendor bills"""
        return {
            'name': _('Add Vendor Bills'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'vendorbill.iourequest',
            'target': 'new',
            'context': {
                'default_iou_request': self.id,
            }
        }

    @api.onchange('requested_amount')
    def onchange_requested_date(self):
        """Update released amount when change the request amount"""
        if self.requested_amount:
            self.write({
                'released_amount': self.requested_amount
            })

    @api.onchange('released_amount')
    def onchange_released_amount(self):
        """Check price difference"""
        if self.released_amount != self.requested_amount:
            self.is_price_change = True
        else:
            self.is_price_change = False

    @api.depends('released_amount', 'expensed_amount', 'expenses_line', 'is_vendor_bill_statement', 'vendor_bills')
    def _compute_balanced_amount(self):
        """Compute balanced amount and expensed amount """
        for rec in self:
            expensed_amount = 0.00
            for lines in self.expenses_line:
                expensed_amount += lines.amount
            # Get expenses amount with vendor bills
            if self.is_vendor_bill_statement:
                for bills in self.vendor_bills:
                    expensed_amount += bills.paid_amount
            rec.expensed_amount = expensed_amount
            rec.balanced_amount = rec.released_amount - expensed_amount

    def button_request_approval_petty_cash_release(self):
        """functions for awaiting_approval petty cash Issued"""
        if self.released_amount == 0.00:
            raise ValidationError("Released Amount is Zero")
        if self.petty_cash_id.cash_balance < self.released_amount:
            raise ValidationError("Exceed the petty cash balance ")
        model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        mail_body = {
            'subject': 'Approval for Petty Cash IOU-Request',
            'msg_type': 'There is a pending IOU request for  your approval.',
            'msg_type2': "%(user_name)s is requesting amount of %(amount)s. Please do the needful." % {'user_name': self.employee_id.name, 'amount': self.currency_id.name + " " + "{:.2f}".format(self.released_amount)},
            'actions': 'confirm'
        }
        return {
            'name': _('Request approval'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'petty.cash.approver.user.wizard',
            'target': 'new',
            'context': {
                        'default_model_id': model.id,
                        'mail_body': mail_body,
                        }
        }

    def button_approve_petty_cash_release(self):
        """functions for Approve petty cash Issue"""
        self.ensure_one()

        if self.petty_cash_id.cash_balance < self.released_amount:
            raise ValidationError("Exceed the petty cash balance ")
        model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        mail_body = {
            'subject': '%s IOU Request has been Approved' % self.name,
            'msg_type': 'The IOU  Request has been  approved.You can proceed. ',
            'status': 'approved',
        }

        return {
            'name': _('Approve'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'petty.cash.approved.comment.wizard',
            'target': 'new',
            'context': {
                        'default_model_id': model.id,
                        'mail_body': mail_body,
                        }
        }

    def button_reject_petty_cash_release(self):
        """functions for Reject petty cash Release"""
        self.ensure_one()
        model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        mail_body = {
            'subject': '%s - IOU Request has been Rejected' % self.name,
            'msg_type': 'The IOU request has been Rejected. ',
        }

        return {
            'name': _('Rejected'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'petty.cash.draft.reason',
            'target': 'new',
            'context': {'default_petty_cash_out_id': self.id,
                        'default_model_id': model.id,
                        'mail_body': mail_body,
                        }
        }

    def button_petty_cash_released(self):
        """functions for released petty cash to employee"""
        self.ensure_one()
        if self.petty_cash_id and self.petty_cash_id.cash_flow < self.released_amount:
            raise ValidationError(_("No cash in the petty cash. Request a petty cash first"))

        move_id = self.create_journal_entries()
        self.move_id = [(4, move_id.id)]
        self.calculate_petty_cash_transactions()
        self.state = "released"

    def create_reimbursement_for_over_balance(self, over_balance):
        """Create a reimbursement for over balance"""
        reimbursement_vals = {
            'petty_cash_id': self.petty_cash_id.id,
            'iou_request_id': self.id,
            'iou_balance': over_balance,
            'employee_id': self.employee_id.id,
            'remarks': 'Balance for %s' % self.name,
        }
        reimbursement_obj = self.env['petty.cash.out'].create(reimbursement_vals)
        self.reimbursement_id = reimbursement_obj.id

    def button_confirmation_iou_complete(self):
        """Button for complete IOU porcess
            ** check Expenses is greater than the approved amount
            ** open the wizard and create reimbursement for extra expenses
        """

        message = ""
        if self.expensed_amount > self.released_amount and not self.reimbursement_id:
            over_balance = "{:.2f}".format(self.expensed_amount - self.released_amount)
            message = "Expensed amount exceeds by %s . " \
                      "Do you want to create a Reimbursement for balance amount :- %s ." % (over_balance, over_balance)
            return {
                'name': _('Confirmation'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'iou.confirmation.wizard',
                'target': 'new',
                'context': {
                    'default_iou_request': self.id,
                    'default_currency_id': self.currency_id.id,
                    'default_message': message,
                }
            }
        else:
            self.button_petty_cash_complete()

    def button_petty_cash_complete(self):
        """functions for Done petty cash and create journal entries for remaining balance"""
        self.ensure_one()
        if not self.expensed_amount or self.expensed_amount == 0.00:
            raise ValidationError(_("Please add expenses lines or Vendor Bills"))

        if self.expensed_amount > self.released_amount:
            over_balance = self.expensed_amount - self.released_amount
            if not self.reimbursement_id:
                self.create_reimbursement_for_over_balance(over_balance)
                self.state = 'open'
                return self.button_view_balance_reimbursement()
            elif self.reimbursement_id.state != 'complete':
                raise ValidationError("Complete the process of balance reimbursements- %s" % self.reimbursement_id.name)
            # raise ValidationError(_("Expensed amount exceeds by %(amount)s. Please create a reimbursement record to settle the extra %(amount)s." % {'amount': over_balance}))

        for line in self.expenses_line:
            #   Create journal entries for expenses ony by one
            journal_entry = self.create_journal_entries_for_expenses(line)
            self.move_id = [(4, journal_entry.id)]

        if self.is_vendor_bill_statement:
            for line in self.vendor_bills:
                #   Create journal entries for Vendor Bills ony by one
                journal_entry = self.create_journal_entries_for_vendor_bills(line)
                self.move_id = [(4, journal_entry.id)]

        if self.balanced_amount > 0.00:
            #    create a journal entry for balance amount
            move_id = self.create_journal_entries_balance(self.balanced_amount)
            #   Update petty cash with balance
            self.petty_cash_id.cash_out -= self.balanced_amount
            self.move_id = [(4, move_id.id)]

        # entries reconcile
        account_move_ids = []
        if self.reimbursement_id:
            """If available reimbursements"""
            account_move_ids += self.reimbursement_id.move_id.line_ids
        for rec in self.move_id:
            account_move_ids += rec.line_ids
        account_move_lines_to_reconcile = self.env['account.move.line']

        for line in account_move_ids:
            if line.account_id.account_type == 'asset_receivable' and not line.reconciled:
                account_move_lines_to_reconcile |= line
        account_move_lines_to_reconcile.sudo().reconcile()
        self.petty_cash_line_id.amount = self.expensed_amount
        self.state = "complete"

    def calculate_petty_cash_transactions(self):
        """ functions for calculate petty cash Transactions"""
        if self.petty_cash_id.cash_balance < self.released_amount:
            raise ValidationError("Exceed the cash balance")
        self.petty_cash_id.cash_out += self.released_amount

    def button_view_journal_entries(self):
        """view journal entries related to this"""
        self.ensure_one()
        context = self.env.context.copy()
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action['domain'] = [('id', 'in', self.move_id.ids)]
        action['view_mode'] = 'form'
        action['context'] = context
        return action

    def button_view_balance_reimbursement(self):
        """view Reimbursement entries related to this"""
        self.ensure_one()
        context = self.env.context.copy()
        context.update({'default_petty_cash_id': self.id, 'create': False})
        action = self.env.ref('petty_cash.action_petty_cash_out').read()[0]
        action['domain'] = [('id', '=', self.reimbursement_id.id)]
        action['view_mode'] = 'tree,form'
        action['context'] = context
        return action

    def create_journal_entries(self):
        """Create journal entries for cash Issue"""
        if not self.employee_id.sudo().address_home_id:
            self.employee_id.create_private_address_for_employee()
            # raise ValidationError("Please add a employee private address ")

        entry_vals = {
            'date': self.release_date,
            'journal_id': self.petty_cash_id.journal_id.id,
            'ref': "Petty Cash IOU Issue to Employee - " + str(self.name),
            'company_id': int(self.company_id.id),
            'currency_id': int(self.currency_id.id),
            'line_ids': [

                (0, 0, {
                    'account_id': self.petty_cash_id.journal_id.default_account_id.id,
                    'name': "Petty Cash IOU Issue to Employee - " + str(self.name),
                    'partner_id': self.employee_id.sudo().address_home_id.id,
                    'credit': self.released_amount,
                    'debit': 0.00,
                }),
                (0, 0, {
                    'account_id': self.employee_id.sudo().address_home_id.property_account_receivable_id.id,
                    'name': "Petty Cash IOU Issue to Employee- " + str(self.name),
                    'partner_id': self.employee_id.sudo().address_home_id.id,
                    'credit': 0.00,
                    'debit': self.released_amount,
                })
            ]
        }
        journal_entry = self.env['account.move'].sudo().create(entry_vals)
        journal_entry.sudo().action_post()
        return journal_entry

    def create_journal_entries_for_expenses(self, line):
        """Create journal entries for register expenses of employee"""
        entry_vals = {
            'date': datetime.now().date(),
            'journal_id': self.petty_cash_id.journal_id.id,
            'ref': "Petty Cash IOU reimbursement (%s)- " % line.expense_account_id.name + str(self.name),
            'company_id': int(self.company_id.id),
            'currency_id': int(self.currency_id.id),
            'line_ids': [
                (0, 0, {
                    'account_id': self.employee_id.sudo().address_home_id.property_account_receivable_id.id,
                    'name': "Petty Cash IOU reimbursement - " + str(self.name) + ' - ' + str(line.name),
                    'partner_id': self.employee_id.sudo().address_home_id.id,
                    'credit': line.amount,
                    'debit': 0.00,
                }),
                (0, 0, {
                    'account_id': line.expense_account_id.id,
                    # 'analytic_account_id': line.account_analytic_id.id,
                    'name': "Petty Cash IOU reimbursement - " + str(self.name) + ' - ' + str(line.name),
                    'partner_id': self.employee_id.sudo().address_home_id.id,
                    'credit': 0.00,
                    'debit': line.amount,
                })
            ]
        }
        journal_entry = self.env['account.move'].sudo().create(entry_vals)
        journal_entry.sudo().action_post()
        return journal_entry

    def create_journal_entries_for_vendor_bills(self, line):
        """Create a payment and journal entry for this vendor bill payment"""

        #   create payment
        payment_journal = self.company_id.vendor_bill_journal
        if not payment_journal:
            raise ValidationError("Journal has not been selected for the \"IOU Settlement Journal\" in the configuration")

        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=line.vendor_bill_id.id).create({
            'journal_id': payment_journal.id or False,
            'currency_id': line.currency_id.id,
            'amount': line.paid_amount,
            'payment_date': line.paid_date,
        })._create_payments()

        #   Create A journal entry
        entry_vals = {
            'date': datetime.now().date(),
            'journal_id': self.petty_cash_id.journal_id.id,
            'ref': "Petty Cash reimbursement(Vendor Bill) - " + str(self.name),
            'company_id': int(self.company_id.id),
            'currency_id': int(self.currency_id.id),
            'line_ids': [
                (0, 0, {
                    'account_id': self.employee_id.sudo().address_home_id.property_account_receivable_id.id,
                    'name': "Petty Cash reimbursement(Vendor Bill) - " + str(self.name) + ' - ' + str(line.vendor_bill_id.name),
                    'partner_id': self.employee_id.sudo().address_home_id.id,
                    'credit': line.paid_amount,
                    'debit': 0.00,
                }),
                (0, 0, {
                    'account_id': payment_journal.outbound_payment_method_line_ids[0].payment_account_id.id or False,
                    # 'analytic_account_id': line.account_analytic_id.id,
                    'name': "Petty Cash reimbursement(Vendor Bill)  - " + str(self.name) + ' - ' + str(line.vendor_bill_id.name),
                    'partner_id': self.employee_id.sudo().address_home_id.id,
                    'credit': 0.00,
                    'debit': line.paid_amount,
                })
            ]
        }
        journal_entry = self.env['account.move'].sudo().create(entry_vals)
        journal_entry.sudo().action_post()
        return journal_entry

    def create_journal_entries_balance(self, amount):
        """Create journal entries for cash Update Balance"""
        if not self.employee_id.sudo().address_home_id:
            self.employee_id.create_private_address_for_employee()

        entry_vals = {
            'date': datetime.now().date(),
            'journal_id': self.petty_cash_id.journal_id.id,
            'ref': "Petty Cash IOU Balance - " + str(self.name),
            'company_id': int(self.company_id.id),
            'currency_id': int(self.currency_id.id),
            'line_ids': [
                (0, 0, {
                    'account_id': self.employee_id.sudo().address_home_id.property_account_receivable_id.id,
                    'name': "Petty Cash IOU Balance - " + str(self.name),
                    'partner_id': self.employee_id.sudo().address_home_id.id,
                    'credit': amount,
                    'debit': 0.00,
                }),

                (0, 0, {
                    'account_id': self.petty_cash_id.journal_id.default_account_id.id,
                    'name': "Petty Cash IOU Balance - " + str(self.name),
                    'partner_id': self.employee_id.sudo().address_home_id.id,
                    'credit': 0.00,
                    'debit': amount,
                })
            ]
        }
        journal_entry = self.env['account.move'].sudo().create(entry_vals)
        journal_entry.sudo().action_post()
        return journal_entry

    def change_state_to_awaiting_approval(self, approvar):
        """Change state to awaiting_approvals"""
        self.petty_cash_id.write({
            'accessible_user_ids': [(4, approvar.id)]
        })
        self.state = "awaiting_approval"

    def change_state_to_approve(self):
        """Change state to Approve"""
        self.state = "approved"
        self.approved_date = datetime.now()

    def set_to_draft(self, reason=False):
        """functions for Set to draft petty cash """
        self.ensure_one()
        self.state = "draft"

    def button_petty_cash_request_reject(self, reason):
        """functions for Cancel petty cash """
        self.ensure_one()
        self.state = "reject"
        self.approver_comment = reason
        self.approved_date = datetime.now()
        self.approved_by = self.env.user


class PettyCashReleaseLine(models.Model):
    """Petty cash out lines class"""
    _name = "petty.cash.release.line"
    _description = " IOU requests Line"

    def _domain_expense_account_id(self):
        """display  expenses, current liability and current asset accounts"""
        # expenses = self.env.ref('account.data_account_type_expenses').id
        # current_liabilities = self.env.ref('account.data_account_type_current_liabilities').id
        # current_asset = self.env.ref('account.data_account_type_current_assets').id
        # account_type = [expenses, current_liabilities, current_asset]
        # domain = [('user_type_id', '=', account_type)]
        domain = [('account_type', 'in', ['expense', 'liability_current', 'asset_current'])]
        return domain

    name = fields.Char("Description", required=True)
    cash_release_id = fields.Many2one('petty.cash.release', string="IOU Requests")
    company_id = fields.Many2one('res.company', related="cash_release_id.company_id", string="Company")
    expense_account_id = fields.Many2one('account.account', string="Expense Account",
                                         domain=_domain_expense_account_id)
    account_analytic_id = fields.Many2one('account.analytic.account', store=True, string='Analytic Account',
                                          readonly=False)
    attachment_id = fields.Many2many('ir.attachment', 'petty_release_attach_id', 'attach_id', 'release_id', string="Attachment")
    amount = fields.Float("Amount", required=True, default=0.00)

    @api.depends('cash_release_id', 'expense_account_id')
    def _compute_account_analytic_id(self):
        """Map analytic accounts"""
        for rec in self:
            if not rec.account_analytic_id:
                default_analytic_account = rec.env['account.analytic.default'].sudo().account_get(
                    partner_id=rec.cash_release_id.employee_id.sudo().address_home_id.id,
                    user_id=rec.env.uid,
                    date=rec.cash_release_id.release_date,
                    company_id=rec.cash_release_id.company_id.id,
                )
                rec.account_analytic_id = default_analytic_account.analytic_id


class PettyCashVendorBillLines(models.Model):
    """Vendor Bills in Petty cash class"""
    _name = "petty.cash.vendor.bills"
    _description = "Petty Cash in vendor bills"

    iou_request_id = fields.Many2one('petty.cash.release', string="IOU Request")
    partner_id = fields.Many2one('res.partner', string='Vendor')
    vendor_bill_id = fields.Many2one('account.move', string="Vendor Bill")
    amount_total = fields.Float(string='Total', store=True)
    amount_residual = fields.Float(string='Due Amount', store=True)
    paid_date = fields.Date(default=fields.Date.today)
    paid_amount = fields.Float(string='Paid Amount', store=True)
    account_analytic_id = fields.Many2one('account.analytic.account', store=True, string='Analytic Account', readonly=False)
    attachment_id = fields.Many2many('ir.attachment', 'iou_vendor_attach_id', 'attach_id', 'release_id',  string="Attachment")
    currency_id = fields.Many2one('res.currency', string='Currency',  related='iou_request_id.currency_id')

    @api.depends('iou_request_id', 'vendor_bill_id')
    def _compute_account_analytic_id(self):
        """Map analytic accounts"""
        for rec in self:
            if not rec.account_analytic_id:
                default_analytic_account = rec.env['account.analytic.default'].sudo().account_get(
                    partner_id=rec.iou_request_id.employee_id.sudo().address_home_id.id,
                    user_id=rec.env.uid,
                    date=rec.iou_request_id.release_date,
                    company_id=rec.iou_request_id.company_id.id,
                )
                rec.account_analytic_id = default_analytic_account.analytic_id

    def unlink(self):
        """Restrict record delete when transition is completed"""
        if self.iou_request_id.state == 'complete':
            raise ValidationError("Cannot delete the record after complete the IOU request")
        return super(PettyCashVendorBillLines, self).unlink()