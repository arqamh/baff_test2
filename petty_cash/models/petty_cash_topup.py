import calendar
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.http import request
from odoo.exceptions import ValidationError


class PettyCashIN(models.Model):
    """
    Petty cash Handling class for cash in
    """
    _name = "petty.cash.in"
    _description = "Petty Cash Top Up"
    _order = "create_date desc"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char("Number", copy=False, default=lambda self: _('New'))
    request_date = fields.Datetime(string="Requested Date", default=fields.Datetime.now, copy=False,)
    cash_date = fields.Datetime(string="Processed Date", tracking=True, copy=False,)
    petty_cash_id = fields.Many2one("petty.cash", string="Petty Cash Drawer", copy=False, required=True)
    user_id = fields.Many2one("res.users", string="Requested User", default=lambda self: self.env.user,copy=False, required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", required=True, readonly=False,
                                  string='Currency')
    amount = fields.Float(string="Amount", default=0.00, copy=False,  tracking=True)
    check_amount_in_words = fields.Char(string="Amount in Words", compute='_compute_check_amount_in_words')
    check_to = fields.Char(string="Cheque To")
    memo = fields.Char(string="Memo")
    cheque_no = fields.Char(string="Cheque No")
    cheque_date = fields.Date(string="Cheque Date")
    is_cheque_ac_payee = fields.Boolean(string="A/c Payee", default=False)
    reason = fields.Char(string="Reason")
    note = fields.Char(string="Note")
    approved_by = fields.Many2one("res.users", string="Approved/Rejected User", copy=False, tracking=True)
    approved_date = fields.Datetime(string="Approved/Rejected Date", copy=False, tracking=True)
    approver_comment = fields.Char("Approve/Reject Comment", copy=False, tracking=True)
    petty_cash_journal_id = fields.Many2one('account.journal', related="petty_cash_id.journal_id")
    journal_id = fields.Many2one('account.journal', string="Source Account", domain="[('type','in',('bank','cash')),('id','!=',petty_cash_journal_id)]" )
    payment_method_line = fields.Many2one('account.payment.method.line')
    payment_method_line_ids = fields.Many2many('account.payment.method.line',
                                               compute="_compute_payment_method_line_ids", string="Available Payment Methods")
    move_id = fields.Many2one('account.move', string="Journal Entries", copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('awaiting_approval', 'Awaiting Approval'),
        ('approved', 'Approved'),
        ('reject', 'Rejected'),
        ('toppedup', 'Topped Up')], string="Status", default="draft", tracking=True)

    petty_cash_line_id = fields.Many2one('petty.cash.line', copy=False,)
    summery_report_id = fields.One2many('reimbursement.summary.report', 'petty_cash_topup_id', string='Summary Report')
    is_wizard = fields.Boolean(default=False)
    is_journal_entry_updated = fields.Boolean(default=False)

    @api.model_create_multi
    def create(self, values):
        """Override create method and add a sequence"""
        results = super(PettyCashIN, self).create(values)
        for result in results:
            if result.name == 'New':
                result.name = result.petty_cash_id.topup_sequence_id.next_by_id()

            #   Create a log un relevant petty cash logins after finished
            cash_line_id = self.env['petty.cash.line'].create({
                'name': result.name,
                'petty_cash_id': result.petty_cash_id.id,
                'from_acc': False,
                'to_acc': result.petty_cash_id.journal_id.default_account_id.id,
                'reason': result.reason,
                'amount': result.amount,
                'user_id': result.user_id.id,
                'approved_by': False,
                'petty_cash_in': result.id,
            })
            result.petty_cash_line_id = cash_line_id.id
            result.petty_cash_id.write({
                'is_available_topup': False,
                'increased_float_amount': 0.00
            })
        return results

    def write(self, vals):
        """Override Write method"""
        res = super(PettyCashIN, self).write(vals)
        if res:
            #   Update log in petty cash
            self.petty_cash_line_id.write({
                'from_acc': self.journal_id.default_account_id if self.journal_id else False,
                'reason': self.reason,
                'amount': self.amount,
                'user_id': self.user_id.id,
                'approved_by': self.approved_by.id if self.approved_by else False,
            })
        return res

    def _compute_check_amount_in_words(self):
        """Compute amount name as a text"""
        if self:
            for rec in self:
                rec.check_amount_in_words = False
                rec.check_amount_in_words = rec.currency_id.amount_to_text(rec.amount)

    @api.depends('journal_id')
    def _compute_payment_method_line_ids(self):
        """Get all available payment lines"""
        for record in self:
            if record.journal_id:
                all_methods = record.journal_id._get_available_payment_method_lines('outgoing')
                record.payment_method_line_ids = [(6, 0, all_methods.ids)]
            else:
                record.payment_method_line_ids = False

    def button_awaiting_approval_petty_cash_in(self):
        """functions for awaiting_approval petty cash IN"""
        self.ensure_one()
        if not self.amount or not self.amount > 0.00:
            raise ValidationError("The amount must be more than Zero")
        model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        mail_body = {
            'subject': 'Request Approval for Petty Cash Top-Up',
            'msg_type': '%(user_name)s is requesting an amount of %(amount)s for petty cash top up' % {'user_name': self.user_id.name, 'amount': self.currency_id.name + " " + "{:.2f}".format(self.amount)},
            'actions': 'confirm'
        }
        return {
            'name': _('Request for Approval'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'petty.cash.approver.user.wizard',
            'target': 'new',
            'context': {'default_petty_cash_out_id': self.id,
                        'default_model_id': model.id,
                        'mail_body': mail_body,
                        }
        }

    def button_approve_petty_cash_in(self):
        """functions for Approve petty cash IN"""
        self.ensure_one()
        if not self.journal_id:
            raise ValidationError(_("Please add a source account to the transaction"))
        model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        mail_body = {
            'subject': '%s - Petty Cash Top-Up has been approved' % self.name,
            'msg_type': 'The Petty Cash Top-Up request has been approved. You can proceed.',
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

    def button_reject_petty_cash_in(self):
        """functions for Reject petty cash IN"""
        self.ensure_one()
        model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        mail_body = {
            'subject': '%s - Petty Cash Top-Up has been Rejected' % self.name,
            'msg_type': 'The Petty Cash Top-Up request has been Rejected.',
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

    def button_petty_cash_toppedup(self):
        """functions for toppedup petty cash IN"""
        self.ensure_one()
        if not self.cash_date:
            self.cash_date = datetime.now()
        self.calculate_petty_cash_transactions()
        self.state = 'toppedup'

    def update_journal_entry(self):
        """Recorect journal entry accounts mapping issues"""
        if not self.payment_method_line:
            raise ValidationError("Select a Payment method for the transactions ")
        outbound_account = self.payment_method_line.payment_account_id
        if not outbound_account:
            raise ValidationError("Select a outstanding payment account for the payment line in the Source journal")
        if self.move_id:
            self.move_id.button_draft()
            line_details = self.move_id.line_ids.filtered(lambda line: line.account_id.id == self.journal_id.default_account_id.id)
            line_details.write({
                'account_id': outbound_account.id
            })
            self.move_id.action_post()
            self.write({
                'is_journal_entry_updated': True
            })


    def calculate_petty_cash_transactions(self):
        """ functions for calculate petty cash Transactions"""
        journal_entry_id = self.create_journal_entries()
        amount = self.petty_cash_id.cash_flow + self.amount
        self.petty_cash_id.write({
            #   update amount in petty cash drawer
            'cash_flow': amount
        })
        self.write({
            'move_id': journal_entry_id.id,
            'is_journal_entry_updated': True,
        })

    def create_journal_entries(self):
        """Create journal entries"""
        outbound_account = self.payment_method_line.payment_account_id
        if not outbound_account:
            raise ValidationError("Select a outstanding payment account for the payment line in the Source journal")
        entry_vals = {
            'date': self.cash_date,
            'journal_id': self.petty_cash_id.journal_id.id,
            'ref': "Petty Cash Top Up - " + str(self.name),
            'company_id': int(self.company_id.id),
            'currency_id': int(self.currency_id.id),
            'line_ids': [
                (0, 0, {
                    'account_id': outbound_account.id,
                    'name': "Petty Cash Top Up - " + str(self.name),
                    'credit': self.amount,
                    'debit': 0.00,
                }),
                (0, 0, {
                    'account_id': self.petty_cash_id.journal_id.default_account_id.id,
                    'name': "Petty Cash Top Up - " + str(self.name),
                    'credit': 0.00,
                    'debit': self.amount,
                })
            ]
        }
        journal_entry = self.env['account.move'].sudo().create(entry_vals)
        journal_entry.sudo().action_post()
        return journal_entry

    def change_state_to_awaiting_approval(self, approvar):
        """Change state to awaiting_approval"""
        self.petty_cash_id.write({
            'accessible_user_ids': [(4, approvar.id)]
        })
        self.state = "awaiting_approval"

    def change_state_to_approve(self):
        """Change state to Approve"""

        self.state = "approved"
        self.approved_date = datetime.now()

    def button_petty_cash_request_reject(self, reason):
        """functions for Cancel petty cash """
        self.ensure_one()
        self.state = "reject"
        self.approved_by = self.env.user
        self.approver_comment = reason
        self.approved_date = datetime.now()

    def set_to_draft(self, reason=False):
        """functions for Set to draft petty cash """
        self.ensure_one()
        self.is_wizard = True
        self.state = "draft"

    def button_view_journal_entries(self):
        """view journal entries related to this"""
        self.ensure_one()
        context = self.env.context.copy()
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action['domain'] = [('id', 'in', self.move_id.ids)]
        action['view_mode'] = 'form'
        action['context'] = context
        return action
