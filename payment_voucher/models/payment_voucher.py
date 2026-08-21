from datetime import datetime, timedelta
from functools import partial
from itertools import groupby

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from collections import defaultdict
from odoo.tools.misc import clean_context
from odoo.http import request


class PaymentVoucher(models.Model):
    _name = 'payment.voucher'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin', 'analytic.mixin']
    _description = 'Payment Voucher'

    @api.depends('voucher_lines.net_amount')
    def _amount_all(self):
        """
        Compute the total amounts of the lines.
        """
        for voucher in self:
            amount_total = 0.0
            for line in voucher.voucher_lines:
                amount_total += line.net_amount
            voucher.update({
                'amount': amount_total,
            })

    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company)
    name = fields.Char('Payment Voucher No', copy=False)
    date = fields.Date('Date', default=fields.Date.context_today, tracking=True)
    cheque_no = fields.Char('Cheque No', tracking=True)
    cheque_date = fields.Date('Cheque Date', tracking=True)
    remarks = fields.Text('Remark', tracking=True)
    amount = fields.Monetary(string='Amount', store=True, readonly=True, compute='_amount_all')
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency', default=lambda self: self.env.company.currency_id.id, tracking=True)
    voucher_lines = fields.One2many('payment.voucher.line', 'voucher_id', string='Voucher Lines', copy=True,
                                    auto_join=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval', 'Waiting For Approval'),
        ('approved', 'Approved'),
        ('post', 'Posted'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, default='draft', tracking=True)
    journal_id = fields.Many2one('account.journal', string='Bank Account', required=True,
                                 check_company=True, domain="[('type', '=', 'bank')]", tracking=True)
    payment_method_line = fields.Many2one('account.payment.method.line')
    payment_method_line_ids = fields.Many2many('account.payment.method.line', compute="_compute_payment_method_line_ids")
    amount_in_words = fields.Char(string="Amount in Words", compute='_get_amount_in_words')
    custom_url = fields.Char("URL")
    approved_by = fields.Many2one('res.users', string="Approved/Rejected By", readonly=1, tracking=True)
    approve_Date = fields.Date(string="Approved/Rejected Date", readonly=1, tracking=True)
    comment = fields.Text(string="Approved/Rejected Comment", readonly=1, tracking=True)
    triggered_approval = fields.Boolean(string="Triggered Approval", default=False)
    partner_id = fields.Many2one(comodel_name='res.partner', string='Partner', tracking=True)
    payee = fields.Char(string='Payee', tracking=True)
    is_cheque_ac_payee = fields.Boolean(string="A/c Payee", default=False)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """Onchange Partner ID set payee"""
        self.payee = self.partner_id.name

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        """Get currency when change the journal"""
        self.currency_id = self.journal_id.currency_id or self.journal_id.company_id.currency_id

    @api.depends('journal_id')
    def _compute_payment_method_line_ids(self):
        """Get all available payment lines"""
        for record in self:
            if record.journal_id:
                all_methods = record.journal_id._get_available_payment_method_lines('outgoing')
                record.payment_method_line_ids = [(6,0, all_methods.ids)]
                cheque_method = all_methods.filtered(lambda method: method.name == 'Cheque')
                if cheque_method:
                    record.payment_method_line = cheque_method.id
                else:
                    manual = all_methods.filtered(lambda method: method.code == 'manual')
                    record.payment_method_line = manual.id if manual else False

            else:
                record.payment_method_line_ids = False

    def _get_amount_in_words(self):
        """Get amount in words"""
        for line in self:
            line.amount_in_words = str(line.currency_id.amount_to_text(line.amount))

    def view_je(self):
        """View related JE"""
        self.ensure_one()
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action['domain'] = [('voucher_id', '=', self.id)]
        action['view_mode'] = 'tree'
        action['search_view_id'] = {}
        return action

    def action_post(self):
        """Post the Payment voucher and post the journal entry"""
        first_approval = self.env['ir.config_parameter'].sudo().get_param(
            'payment_voucher.payment_voucher_approval')
        if first_approval:
            if not self.triggered_approval:
                model = self.env['ir.model'].search([('model', '=', request.params.get('model'))])
                return {
                    'name': _('Send to Approval'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'payment.voucher.approver.user.wizard',
                    'target': 'new',
                    'context': {'default_voucher_id': self.id,
                                'default_model_id': model.id}
                }
        #   inbound
        outbound_account = self.payment_method_line.payment_account_id
        if not outbound_account:
            raise ValidationError("Select a outstanding payment account for the payment line in the journal")
        amount_company_currency = self.currency_id._convert(self.amount, self.company_id.currency_id, self.company_id, self.date)
        entry_list = [(0, 0, {'debit': 0.0, 'credit': amount_company_currency, 'amount_currency': -self.amount, 'date_maturity': self.date,
                              'account_id': outbound_account.id, 'partner_id': self.partner_id.id,
                              'analytic_distribution': self.analytic_distribution,
                              'currency_id': self.currency_id.id,
                              'name': f"{self.name} (Cheque No - {self.cheque_no})"

                              })]
        for debit in self.voucher_lines:
            debit_company_currency = self.currency_id._convert(debit.net_amount, self.company_id.currency_id,
                                                                self.company_id, self.date)

            entry_list.append((0, 0, {'debit': debit_company_currency, 'credit': 0.0, 'amount_currency': debit.net_amount, 'date_maturity': self.date,
                                      'account_id': debit.account_id.id, 'partner_id': debit.partner_id.id,
                                      'analytic_distribution': debit.analytic_distribution,
                                      'currency_id': self.currency_id.id, 'name': f"{debit.label , self.name} (Cheque No - {self.cheque_no})" }))
        je = self.env['account.move'].create({
            'move_type': 'entry',
            'date': self.date,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id.id,
            'ref': self.name,
            'line_ids': entry_list,
            'voucher_id': self.id
        })
        self.sudo().write({
            'state': 'post'
        })

        je.action_post()
        return True

    def action_cancel(self):
        move_obj = self.env['account.move'].search([('voucher_id', '=', self.id)])
        move_obj.button_cancel()

        self.sudo().write({
            'state': 'cancel',
            'triggered_approval': False,
        })
        return True

    def reset_draft(self):
        self.sudo().write({
            'state': 'draft',
            'triggered_approval': False,
        })

    def approve_transfer(self):
        model = self.env['ir.model'].search([('model', '=', request.params.get('model'))])
        return {
            'name': _('Comment'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'payment.voucher.approve.comment.wizard',
            'target': 'new',
            'context': {'default_voucher_id': self.id,
                        'default_model_id': model.id,
                        'default_action': self._context.get('action') or False,
                        }
        }

    def reject_transfer(self):
        model = self.env['ir.model'].search([('model', '=', request.params.get('model'))])
        return {
            'name': _('Comment'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'payment.voucher.approve.comment.wizard',
            'target': 'new',
            'context': {'default_voucher_id': self.id,
                        'default_model_id': model.id,
                        'default_action': self._context.get('action') or False,
                        }
        }

    @api.model
    def create(self, vals):
        """Call for the relates Voucher sequence and get the number to create the form"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('payment.voucher') or _('New')

        result = super(PaymentVoucher, self).create(vals)
        return result

    def unlink(self):
        """Cannot delete Posted and Cancelled Payment Vouchers"""
        if self.state == 'draft':
            return self.unlink()
        else:
            raise UserError('You can delete Draft Vouchers only.')


class PaymentVoucherLines(models.Model):
    _name = 'payment.voucher.line'
    _inherit = ['analytic.mixin']
    _description = "Payment Voucher Line"

    voucher_id = fields.Many2one('payment.voucher', string='Voucher No', required=True, ondelete='cascade', index=True,
                                 copy=False)
    account_id = fields.Many2one(
        comodel_name='account.account',
        string='Account',
        domain="[]",
        check_company=True)
    label = fields.Char('Label')
    partner_id = fields.Many2one('res.partner', string='Partner')
    net_amount = fields.Float('Net Amount')


class InheritAccountMove(models.Model):
    _inherit = ['account.move']

    voucher_id = fields.Many2one('payment.voucher', string='Voucher No')


