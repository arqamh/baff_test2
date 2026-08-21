#####################################################
# There are two way to manage petty cash reimbursement
# 1. normal reimbursement record
# 2. special reimbursement for manage balance in IOU request
#     'iou_request_id' field use To check special reimbursement
#####################################################

import calendar
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.http import request


class PettyCashOut(models.Model):
    """
    Petty cash Handling class
    """
    _name = "petty.cash.out"
    _description = "Petty Cash Out"
    _order = "create_date desc"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin', 'analytic.mixin']

    name = fields.Char("Number", copy=False, default=lambda self: _('New'))
    cash_date = fields.Datetime(string="Requested Date", default=fields.Datetime.now)
    petty_cash_id = fields.Many2one("petty.cash", string="Petty cash Drawer", required=True)
    iou_request_id = fields.Many2one("petty.cash.release", string="IOU Request")
    petty_cash_line_id = fields.Many2one('petty.cash.line', copy=False)
    employee_id = fields.Many2one('hr.employee', string="Requested Employee", required=True)
    user_id = fields.Many2one("res.users", string="User", default=lambda self: self.env.user, copy=False)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", required=True, readonly=False,
                                  string='Currency')
    iou_balance = fields.Float(string="IOU Balance", copy=False, default=0.00, tracking=True,)
    expensed_amount = fields.Float(string="Total Amount", copy=False, default=0.00, compute="compute_expensed_amount", tracking=True, store=True)

    expenses_line = fields.One2many('petty.cash.out.line', 'cash_out_id', copy=False, string="Cash Lines")
    reason = fields.Many2one('petty.cash.reason')
    reject_reason = fields.Char('Reject Reason')
    requested_approver = fields.Many2one("res.users", string="Requested First Approver", copy=False)
    approved_by = fields.Many2one("res.users", string="Approved/rejected User", copy=False)
    approver_comment = fields.Char('Approve/reject Comment', copy=False)
    approved_date = fields.Datetime(string="Approved/Rejected Date", copy=False, tracking=True)
    move_id = fields.Many2many('account.move', 'cash_out_move_rel', 'cash_out_id', 'move_id', string="Journal Entries", copy=False)
    is_approve = fields.Boolean(default=False)
    is_exceed_the_minimum = fields.Boolean("Exceed the minimum amount", copy=False, store=True, compute="compute_is_exceed_the_minimum")

    approval_level = fields.Selection([
        ('first_approve', 'First approve'),
        ('second_approve', 'Second approve')
    ], string="Approve Level", default=False)
    is_reversed_entry = fields.Boolean(default=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('awaiting_approval', 'Awaiting Approval'),
        ('second_awaiting_approval', 'waiting for Second Approval'),
        ('approved', 'Approved'),
        ('reject', 'Rejected'),
        ('complete', 'Completed')], string="Status", default="draft", tracking=True)
    is_wizard = fields.Boolean(default=False)
    remarks = fields.Text()
    checked_by = fields.Many2one('res.users', string="Checked By", tracking=True)
    cheque_no = fields.Char()

    cheque_date = fields.Date(string="Cheque Date")
    is_cheque_ac_payee = fields.Boolean(string="A/c Payee", default=False)

    @api.model_create_multi
    def create(self, values):
        """Override create method and add a sequence"""
        results = super(PettyCashOut, self).create(values)
        for result in results:
            if result.name == 'New':
                result.name = result.petty_cash_id.rem_sequence_id.next_by_id()
            # create a log in petty cash list
            cash_line_id = self.env['petty.cash.line'].create({
                'name': result.name,
                'petty_cash_id': result.petty_cash_id.id,
                'from_acc': result.petty_cash_id.journal_id.default_account_id.id,
                'to_acc': self.employee_id.sudo().address_home_id.property_account_payable_id.id if self.employee_id.sudo().address_home_id else False,
                'reason': result.reason.name if result.reason else '',
                'amount': result.expensed_amount,
                'user_id': result.user_id.id,
                'employee_id': result.employee_id.id,
                'approved_by': result.approved_by.id,
                'cash_reimbursement_id': result.id,
            })
            result.petty_cash_line_id = cash_line_id.id
        return results

    def write(self, vals):
        """Override Write method"""
        res = super(PettyCashOut, self).write(vals)
        if res:
            #   Update log in petty cash
            if not self.employee_id.sudo().address_home_id:
                to_account = False
            elif self.iou_request_id:
                to_account = self.employee_id.sudo().address_home_id.property_account_receivable_id.id
            else:
                to_account = self.employee_id.sudo().address_home_id.property_account_payable_id.id
            self.petty_cash_line_id.write({
                'to_acc': to_account,
                'reason': self.reason.name if self.reason else '',
                'amount': self.expensed_amount,
                'user_id': self.user_id.id,
                'approved_by': self.approved_by.id if self.approved_by else False,
            })
        return res

    @api.depends('expenses_line')
    def compute_expensed_amount(self):
        """Calculate expensed amount"""
        for rec in self:
            expenced_amount = 0.00
            for expenced in rec.expenses_line:
                expenced_amount += expenced.amount
            rec.expensed_amount = expenced_amount + rec.iou_balance
            rec.update_approval_level()

    def update_approval_level(self):
        """Check minimum amount in configurations and check current amount exceed the limit"""
        first_minimum_amount = self.env['ir.config_parameter'].sudo().get_param(
            'petty_cash.minimum_amount_for_petty_cash') or False
        second_minimum_amount = self.env['ir.config_parameter'].sudo().get_param(
            'petty_cash.amount_for_petty_cash_second_level') or False
        approve_group = False
        if second_minimum_amount and float(second_minimum_amount) < self.expensed_amount:
            self.approval_level = 'second_approve'
            approve_group = self.env.ref('petty_cash.petty_cash_group_director').id
        elif first_minimum_amount and float(first_minimum_amount) < self.expensed_amount:
            self.approval_level = 'first_approve'
            approve_group = self.env.ref('petty_cash.petty_cash_group_manager').id
        else:
            self.approval_level = False
            approve_group = False

        return approve_group

    def button_awaiting_approval_petty_cash_out(self):
        """functions for awaiting_approval petty cash Out"""
        self.ensure_one()
        if not self.expenses_line and self.iou_balance == 0:
            # after pay and request reimbursements
            raise ValidationError("Please add Expenses and amounts.")

        model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        approve_level = self.update_approval_level()
        mail_body = {
            'subject': 'Request Approval for Petty Cash Reimbursement',
            'msg_type': 'There is a reimbursement request for  your approval.',
            'msg_type2': " %(user_name)s is \
                      requesting an amount of %(amount)s. Please do the needful.""" % {
                'user_name': self.employee_id.name,
                'amount': self.currency_id.name + " " + "{:.2f}".format(self.expensed_amount)},
            'actions': 'confirm',

        }
        return {
            'name': _('Request Approval'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'petty.cash.approver.user.wizard',
            'target': 'new',
            'context': {'default_petty_cash_out_id': self.id,
                        'default_model_id': model.id,
                        'mail_body': mail_body,
                        'approve_group': approve_level
                        }
        }

    def petty_cash_out_email_approved(self):
        """Send email after approve the IOU requests"""
        model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        mail_body = {
            'subject': '%s Reimbursement has been Approved' % self.name,
            'msg_type': 'The reimbursement has been  approved.You can proceed. ',
            'status': 'approved',
        }

        return {
            'name': _('Approve'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'petty.cash.approved.comment.wizard',
            'target': 'new',
            'context': {'default_petty_cash_out_id': self.id,
                        'default_model_id': model.id,
                        'mail_body': mail_body,
                        }
        }

    def button_reject_petty_cash_out(self):
        """functions for Reject petty cash Out"""
        self.ensure_one()
        model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        mail_body = {
            'subject': '%s - Reimbursement has been Rejected' % self.name,
            'msg_type': 'The Reimbursement request has been Rejected.',
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

    def button_approve_petty_cash_out(self):
        """functions for Approve petty cash Out"""
        self.ensure_one()

        if self.petty_cash_id and self.petty_cash_id.cash_flow < self.expensed_amount:
            raise ValidationError(_("No cash in the petty cash Drawer. Please topup the petty cash "))
        return self.petty_cash_out_email_approved()

    def button_reimbursement_petty_cash_out(self):
        """Change state to a complete with transactions
        """
        self.ensure_one()

        if not self.expenses_line and not self.iou_request_id:
            raise ValidationError("Please add Expenses lines and amounts.")

        if self.petty_cash_id.cash_balance < self.expensed_amount:
            raise ValidationError("Exceed the petty cash drawer Balance")

        for line in self.expenses_line:
            # create journal entries for expenses line
            expense = self.cash_out_register_expense(line)
            if expense:
                self.move_id = [(4, expense.id)]

        #   transfer to the employee
        if self.expenses_line:
            # create journal entries for normal reimbursement
            move = self.cash_out_cash_transfer_to_employee(line)
            if move:
                self.move_id = [(4, move.id)]

        if self.iou_request_id:
            # create journal entries for special reimbursement from IOU request
            reimburse_balance = self.cash_iou_balance_transfer_to_employee()
            if reimburse_balance:
                self.move_id = [(4, reimburse_balance.id)]

        #   reconcile transactions
        self.sudo().bank_reconcile()
        self.petty_cash_id.cash_out += self.expensed_amount
        self.state = "complete"

    def bank_reconcile(self):
        """Reconcile accounts transactions"""
        account_move_ids = []
        for rec in self.move_id:
            account_move_ids += rec.line_ids
        account_move_lines_to_reconcile = self.env['account.move.line']

        for line in account_move_ids:
            if line.account_id.account_type == 'liability_payable' and not line.reconciled:
                account_move_lines_to_reconcile |= line
        account_move_lines_to_reconcile.sudo().reconcile()

    def create_transactions_in_petty_cash(self):
        #   Create a log un relevant petty cash logins after finished
        if self.is_reversed_entry and self.petty_cash_line_id:
            self.petty_cash_line_id.write({
                'name': self.name,
                'petty_cash_id': self.petty_cash_id.id,
                'from_acc': self.petty_cash_id.journal_id.default_account_id.id,
                'to_acc': self.employee_id.sudo().address_home_id.property_account_payable_id.id,
                'reason': self.reason.name,
                'amount': self.expensed_amount,
                'type': 'reimbursement',
                'user_id': self.user_id.id,
                'employee_id': self.employee_id.id,
                'approved_by': self.approved_by.id,
                'cash_reimbursement_id': self.id,
            })
        else:
            cash_line_id = self.env['petty.cash.line'].create({
                    'name': self.name,
                    'petty_cash_id': self.petty_cash_id.id,
                    'from_acc': self.petty_cash_id.journal_id.default_account_id.id,
                    'to_acc': self.employee_id.sudo().address_home_id.property_account_payable_id.id,
                    'reason': self.reason.name,
                    'amount': self.expensed_amount,
                    'type': 'reimbursement',
                    'user_id': self.user_id.id,
                    'employee_id': self.employee_id.id,
                    'approved_by': self.approved_by.id,
                    'cash_reimbursement_id': self.id,
                })
            self.petty_cash_line_id = cash_line_id.id

    def button_set_to_draft_after_approve(self):
        """Reverse journal entries and reimbursements back to draft after approve"""
        if self.state == "complete" and self.move_id:
            journal_ids = self.move_id.filtered(lambda x: not x.is_reversed_journal and not x.reversed_entry_id)
            moves_to_reverse = self.env['account.move'].search([('id', 'in', journal_ids.ids)])
            today = fields.Date.context_today(self)
            default_values_list = [{
                'date': today,
                'ref': _('Reversal of: %s') % move.ref,
            } for move in moves_to_reverse]

            reverse_id = moves_to_reverse.sudo()._reverse_moves(default_values_list, cancel=False)
            for journal in journal_ids:
                journal.is_reversed_journal = True

            for reverse in reverse_id:
                reverse.sudo().action_post()
                self.move_id = [(4, reverse.id)]
            self.petty_cash_id.cash_out -= self.expensed_amount
            self.state = "draft"
            self.is_reversed_entry = True
        else:
            raise ValidationError("Reimbursement is not approved yet")

    def button_petty_cash_request_reject(self, reason):
        """functions for Reject Reimbursement"""
        self.ensure_one()
        self.state = "reject"
        self.approver_comment = reason
        self.approved_date = datetime.now()
        self.approved_by = self.env.user

    def button_function_set_to_draft(self,):
        """functions for Set to draft petty cash """
        self.ensure_one()
        self.state = "draft"

    def button_view_journal_entries(self):
        """view journal entries related to this"""
        self.ensure_one()
        context = self.env.context.copy()
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action['domain'] = [('id', 'in', self.move_id.ids), ]
        action['view_mode'] = 'form'
        action['context'] = context
        action['context'].update({
            'search_default_reversed_move': True,
        })
        return action

    def cash_out_register_expense(self, line):
        """Create journal entries for employee_expenses"""
        if not self.employee_id.sudo().address_home_id:
            self.employee_id.create_private_address_for_employee()
            # raise ValidationError("Please add an employee private address ")
        entry_vals = {
            'date': datetime.now().date(),
            'journal_id': self.petty_cash_id.journal_id.id,
            'ref': "Petty Cash Reimbursement (%s)- " % line.expense_account_id.name + str(self.name),
            'company_id': int(self.company_id.id),
            'currency_id': int(self.currency_id.id),
            'line_ids': [
                (0, 0, {
                    'account_id': self.employee_id.sudo().address_home_id.property_account_payable_id.id,
                    'analytic_distribution': line.analytic_distribution,
                    'name': "Petty Cash Reimbursement - " + str(self.name),
                    'partner_id': self.employee_id.sudo().address_home_id.id,
                    'credit': line.amount,
                    'debit': 0.00,
                }),
                (0, 0, {
                    'account_id': line.expense_account_id.id,
                    'analytic_distribution': line.analytic_distribution,
                    'name': "Petty Cash Reimbursement - " + str(self.name),
                    'partner_id': self.employee_id.sudo().address_home_id.id,
                    'credit': 0.00,
                    'debit': line.amount,
                })
            ]
        }
        journal_entry = self.env['account.move'].sudo().create(entry_vals)
        journal_entry.sudo().action_post()
        return journal_entry

    def change_state_to_approve(self):
        """Change state to awaiting_approval"""
        self.state = "approved"
        self.approved_date = datetime.now()
        self.is_approve = False
        if self.approval_level:
            self.approval_level = False

    def cash_out_cash_transfer_to_employee(self, line):
        """
            Create journal entries to employee in normal reimbursement process
            ** Account - employee payable account
            ** amount  - Total amount of expenses lines
        """
        if not self.employee_id.sudo().address_home_id:
            self.employee_id.create_private_address_for_employee()
            # raise ValidationError("Please add a employee private address ")
        entry_vals = {
            'date': datetime.now().date(),
            'journal_id': self.petty_cash_id.journal_id.id,
            'ref': "Petty Cash Reimbursement to Employee- " + str(self.name),
            'company_id': int(self.company_id.id),
            'currency_id': int(self.currency_id.id),
            'line_ids': [
                (0, 0, {
                    'account_id': self.petty_cash_id.journal_id.default_account_id.id,
                    'analytic_distribution': line.analytic_distribution,
                    'name': "Petty Cash Reimbursement to Employee - " + str(self.name),
                    'partner_id': self.employee_id.sudo().address_home_id.id,
                    'credit':  self.expensed_amount - self.iou_balance,
                    'debit': 0.00
                }),
                (0, 0, {
                    'account_id': self.employee_id.sudo().address_home_id.property_account_payable_id.id,
                    'analytic_distribution': line.analytic_distribution,
                    'name': "Petty Cash Reimbursement to Employee - " + str(self.name),
                    'partner_id': self.employee_id.sudo().address_home_id.id,
                    'credit': 0.00,
                    'debit': self.expensed_amount - self.iou_balance,
                })
            ]
        }
        journal_entry = self.env['account.move'].sudo().create(entry_vals)
        journal_entry.sudo().action_post()
        return journal_entry

    def cash_iou_balance_transfer_to_employee(self):
        """
            Create journal entries to employee in Special reimbursement process
            ** Account - employee receivable account
            ** amount  - Balance amount of IOU request
        """
        if not self.employee_id.sudo().address_home_id:
            self.employee_id.create_private_address_for_employee()
            # raise ValidationError("Please add a employee private address ")
        entry_vals = {
            'date': datetime.now().date(),
            'journal_id': self.petty_cash_id.journal_id.id,
            'ref': "Petty Cash balance Reimbursement to Employee- " + str(self.name),
            'company_id': int(self.company_id.id),
            'currency_id': int(self.currency_id.id),
            'line_ids': [
                (0, 0, {
                    'account_id': self.petty_cash_id.journal_id.default_account_id.id,
                    'name': "Petty Cash balance Reimbursement to Employee - " + str(self.name),
                    'partner_id': self.employee_id.sudo().address_home_id.id,
                    'credit':  self.iou_balance,
                    'debit': 0.00
                }),
                (0, 0, {
                    'account_id': self.employee_id.sudo().address_home_id.property_account_receivable_id.id,
                    'name': "Petty Cash balance Reimbursement to Employee - " + str(self.name),
                    'partner_id': self.employee_id.sudo().address_home_id.id,
                    'credit': 0.00,
                    'debit': self.iou_balance,
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
        approve_group = self.update_approval_level()
        self.state = "awaiting_approval"
        self.requested_approver = approvar.id


class PettyCashOutLine(models.Model):
    """Petty cash out lines class"""
    _name = "petty.cash.out.line"
    _inherit = ['analytic.mixin']
    _description = "Petty Cash Out Line"

    def _domain_expense_account_id(self):
        """display  expenses, current liability and current asset accounts"""
        # expenses = self.env.ref('account.expense').id
        # current_liabilities = self.env.ref('account.liability_current').id
        # current_asset = self.env.ref('account.asset_current').id
        # account_type = [expenses, current_liabilities, current_asset]
        domain = [('account_type', 'in', ['expense', 'liability_current', 'asset_current'])]
        return domain

    name = fields.Char("Description", required=True)
    cash_out_id = fields.Many2one('petty.cash.out', string="Petty Cash")
    company_id = fields.Many2one('res.company', related="cash_out_id.company_id", string="Company")
    expense_account_id = fields.Many2one('account.account', string="Expense Account", required=True,
                                         domain=_domain_expense_account_id)
    account_analytic_id = fields.Many2one('account.analytic.account', store=True, string='Analytic Account', readonly=False)
    attachment_id = fields.Many2many('ir.attachment', 'petty_attach_id', 'attach_id', 'petty_id', string="Attachment")
    amount = fields.Float("Amount", required=True, default=0.00)

    @api.depends('cash_out_id', 'expense_account_id')
    def _compute_account_analytic_id(self):
        """Map analytic accounts"""
        for rec in self:
            if not rec.account_analytic_id:
                default_analytic_account = rec.env['account.analytic.default'].sudo().account_get(
                    partner_id=rec.cash_out_id.employee_id.sudo().address_home_id.id,
                    user_id=rec.env.uid,
                    date=rec.cash_out_id.cash_date,
                    company_id=rec.cash_out_id.company_id.id,
                )
                rec.account_analytic_id = default_analytic_account.analytic_id


class IrAttachment(models.Model):
    """Inherit Attachments class  """
    _inherit = 'ir.attachment'

    petty_attach_id = fields.Many2many('petty.cash.out.line', 'petty_attach_id', 'petty_id', 'attach_id', string="Petty cash")
    petty_release_id = fields.Many2many('petty.cash.release.line', 'petty_release_attach_id', 'release_id', 'attach_id',
                                        string="IOU Requests")