from odoo import api, exceptions, fields, models, _
from odoo.tools import float_is_zero
    
    
class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"
    
    pdc_id = fields.Many2one('pdc.wizard')


class AccountInvoice(models.Model):
    _inherit = "account.move"
    
    def open_pdc_payment(self):
        """Action for open pdc payment"""
        if self.pdc_payment_ids[0].payment_type == 'receive_money':
            [action] = self.env.ref('sh_pdc.sh_pdc_payment_menu_action_customers').read()
        else:
            [action] = self.env.ref('sh_pdc.sh_pdc_payment_menu_action_vendors').read()
        action['domain'] = [('id', 'in', self.pdc_payment_ids.ids)]
        return action
    
#     
#     
#     def _get_reconciled_info_JSON_values(self):
#         
#         reconciled_vals = super(AccountInvoice, self)._get_reconciled_info_JSON_values()
#         if self.pdc_payment_ids:
#             for pdc_payment in self.pdc_payment_ids.filtered(lambda x:x.state == 'done'):
#                 reconciled_vals.append({
#                     'name': pdc_payment.name,
#                     'journal_name': pdc_payment.journal_id.name,
#                     'amount': pdc_payment.payment_amount,
#                     'currency': self.currency_id.symbol,
#                     'digits': [69, self.currency_id.decimal_places],
#                     'position': self.currency_id.position,
#                     'date': pdc_payment.payment_date,
#                     'payment_id': pdc_payment.id,
# #                     'account_payment_id': counterpart_line.payment_id.id,
#                     'payment_method_name': 'Cheque',
# #                     'move_id': counterpart_line.move_id.id,
#                     'ref': pdc_payment.memo,
#                 })
#         return reconciled_vals
    
    def _compute_pdc_payment(self):
        """Compute and get no of pdc payments"""
        for rec in self:
            rec.pdc_payment_count = len(self.pdc_payment_ids)
    
    pdc_id = fields.Many2one('pdc.wizard')
    pdc_payment_ids = fields.Many2many('pdc.wizard',compute='_compute_pdc_payment_invoice')
    pdc_payment_count = fields.Integer("Pdc payment count",compute='_compute_pdc_payment')
    total_pdc_payment = fields.Monetary("Total PDC Amount",compute='_compute_total_pdc')
    total_pdc_pending = fields.Monetary("Total Pending",compute='_compute_total_pdc')
    total_pdc_cancel = fields.Monetary("Total Cancel",compute='_compute_total_pdc')
    total_pdc_received = fields.Monetary("Total Received",compute='_compute_total_pdc')
    
    @api.depends('pdc_payment_ids.state')
    def _compute_total_pdc(self):
        """Compute and calculate total of payments """
        for rec in self:
            rec.total_pdc_payment = 0.0
            rec.total_pdc_pending = 0.0
            rec.total_pdc_cancel = 0.0
            rec.total_pdc_received = 0.0
            if rec.pdc_payment_ids:
                for pdc_payment in rec.pdc_payment_ids:
                    if pdc_payment.state in ('done'):
                        rec.total_pdc_received += pdc_payment.payment_amount
                    elif pdc_payment.state in ('cancel'):
                        rec.total_pdc_cancel += pdc_payment.payment_amount
                    else:
                        rec.total_pdc_pending += pdc_payment.payment_amount
            rec.total_pdc_payment = rec.total_pdc_pending + rec.total_pdc_received + rec.total_pdc_cancel

    def _compute_pdc_payment_invoice(self):
        """Compute and get related invoices"""
        self.pdc_payment_ids = False
        for move in self:
            pdcs = self.env["pdc.wizard"].search([
                ('invoice_id','=',move.id)
                ])
            if pdcs:
                move.pdc_payment_ids = [(6,0,pdcs.ids)]

    def get_reconciled_pdc_cheques(self):
        """Check pending bank reconciled jornal entries in pdsc payment"""
        journal_entries = self.env['account.move.line'].search([('pdc_id', 'in', self.pdc_payment_ids.ids)])
        return any(not entry.full_reconcile_id for entry in journal_entries)

    def _compute_amount(self):
        """Override method and check unreconciled pdc payments"""
        res = super(AccountInvoice, self)._compute_amount()
        for move in self:
            currencies = move._get_lines_onchange_currency().currency_id
            currency = currencies if len(currencies) == 1 else move.company_id.currency_id
            if move._payment_state_matters() and move.state == 'posted' and move.payment_state == "paid":
                if currency.is_zero(move.amount_residual):
                    reconciled_payments = move._get_reconciled_payments()
                    if not reconciled_payments or all(payment.is_matched for payment in reconciled_payments):
                        if move.pdc_payment_ids and move.get_reconciled_pdc_cheques():
                            move.payment_state = 'in_payment'
        return res
            
#     @api.depends(
#         'line_ids.debit',
#         'line_ids.credit',
#         'line_ids.currency_id',
#         'line_ids.amount_currency',
#         'line_ids.amount_residual',
#         'line_ids.amount_residual_currency',
#         'line_ids.payment_id.state',
#         'pdc_payment_ids.state')
#     def _compute_amount(self):
#         invoice_ids = [move.id for move in self if move.id and move.is_invoice(include_receipts=True)]
#         self.env['account.payment'].flush(['state'])
#         if invoice_ids:
#             self._cr.execute(
#                 '''
#                     SELECT move.id
#                     FROM account_move move
#                     JOIN account_move_line line ON line.move_id = move.id
#                     JOIN account_partial_reconcile part ON part.debit_move_id = line.id OR part.credit_move_id = line.id
#                     JOIN account_move_line rec_line ON
#                         (rec_line.id = part.credit_move_id AND line.id = part.debit_move_id)
#                         OR
#                         (rec_line.id = part.debit_move_id AND line.id = part.credit_move_id)
#                     JOIN account_payment payment ON payment.id = rec_line.payment_id
#                     JOIN account_journal journal ON journal.id = rec_line.journal_id
#                     WHERE payment.state IN ('posted', 'sent')
#                     AND journal.post_at = 'bank_rec'
#                     AND move.id IN %s
#                 ''', [tuple(invoice_ids)]
#             )
#             in_payment_set = set(res[0] for res in self._cr.fetchall())
#         else:
#             in_payment_set = {}
# 
#         for move in self:
#             total_untaxed = 0.0
#             total_untaxed_currency = 0.0
#             total_tax = 0.0
#             total_tax_currency = 0.0
#             total_residual = 0.0
#             total_residual_currency = 0.0
#             total = 0.0
#             total_currency = 0.0
#             currencies = set()
#             
#             # check pdc payment
#             related_pdc_payment = 0.0
#             if move.pdc_payment_ids:
#                 for pdc_payment in move.pdc_payment_ids.filtered(lambda x:x.state=='done'):
#                     related_pdc_payment += pdc_payment.payment_amount
#                     
#                     
#             for line in move.line_ids:
#                 if line.currency_id:
#                     currencies.add(line.currency_id)
# 
#                 if move.is_invoice(include_receipts=True):
#                     # === Invoices ===
# 
#                     if not line.exclude_from_invoice_tab:
#                         # Untaxed amount.
#                         total_untaxed += line.balance
#                         total_untaxed_currency += line.amount_currency
#                         total += line.balance
#                         total_currency += line.amount_currency
#                     elif line.tax_line_id:
#                         # Tax amount.
#                         total_tax += line.balance
#                         total_tax_currency += line.amount_currency
#                         total += line.balance
#                         total_currency += line.amount_currency
#                     elif line.account_id.user_type_id.type in ('receivable', 'payable'):
#                         # Residual amount.
#                         total_residual += line.amount_residual
#                         total_residual_currency += line.amount_residual_currency
#                 else:
#                     # === Miscellaneous journal entry ===
#                     if line.debit:
#                         total += line.balance
#                         total_currency += line.amount_currency
# 
#             if move.type == 'entry' or move.is_outbound():
#                 sign = 1
#             else:
#                 sign = -1
#             move.amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
#             move.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)
#             move.amount_total = sign * (total_currency if len(currencies) == 1 else total)
# 
#             move.amount_residual =  -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
#             if related_pdc_payment > 0.0:
#                  move.amount_residual  -= related_pdc_payment
#             move.amount_untaxed_signed = -total_untaxed
#             move.amount_tax_signed = -total_tax
#             move.amount_total_signed = -total
#             move.amount_residual_signed = total_residual
#             if related_pdc_payment > 0.0:
#                  move.amount_residual_signed  -= related_pdc_payment
# 
# 
#             currency = len(currencies) == 1 and currencies.pop() or move.company_id.currency_id
#             is_paid = currency and currency.is_zero(move.amount_residual) or not move.amount_residual
#             
#             # Compute 'invoice_payment_state'.
#             if move.state == 'posted' and is_paid:
#                 if move.id in in_payment_set:
#                     move.invoice_payment_state = 'in_payment'
#                 else:
#                     move.invoice_payment_state = 'paid'
#             else:
#                 move.invoice_payment_state = 'not_paid'
