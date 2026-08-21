# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################

import logging

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
from odoo.tools import frozendict, formatLang, format_date, float_is_zero, float_compare
import functools
from contextlib import ExitStack, contextmanager
from odoo.exceptions import AccessError, UserError, ValidationError


_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    def remove_global_discount(self):
        if self.invoice_line_ids:
            self.invoice_line_ids.write({
                'global_discount_percent': '',
                'global_discount_amount':0
            })
            self.is_global_discount_applied = False
            self.global_order_discount = 0
            self.invoice_line_ids._compute_totals()
            self._compute_amount()

    def action_update_discount(self):
        if self.invoice_line_ids:
            if not self.global_order_discount:
                self.invoice_line_ids.write({
                    'global_discount_percent': '',
                    'global_discount_amount':0
                })
                self.is_global_discount_applied = False
            elif self.global_discount_type == 'percent':
                if self.global_order_discount >100 or self.global_order_discount <0:
                    raise ValidationError("Please enter the valid discount")
                self.invoice_line_ids.write({
                    'global_discount_percent':str(self.global_order_discount/100),
                    'global_discount_amount':0

                })
                self.is_global_discount_applied = True
            else:
                total_amount = 0
                for line in self.invoice_line_ids:
                    discount_type = ''
                    discount_type = line.discount_type
                    quantity = line.quantity
                    if discount_type == 'fixed':
                        line_discount_price_unit = line.price_unit * line.quantity - line.discount
                        quantity = 1.0
                    else:
                        line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
                    total_amount += line_discount_price_unit*quantity
                if total_amount < self.global_order_discount:
                    raise ValidationError("Discount can't be greater than the invoice total amount")
                self.is_global_discount_applied = True
                self.invoice_line_ids.write({
                    'global_discount_percent': str(self.global_order_discount/total_amount),
                    'global_discount_amount':0
                })
            self.invoice_line_ids._compute_totals()
            self._compute_amount()
            self._compute_tax_totals()

    @api.depends(
        'invoice_line_ids.currency_rate',
        'invoice_line_ids.tax_base_amount',
        'invoice_line_ids.tax_line_id',
        'invoice_line_ids.price_total',
        'invoice_line_ids.price_subtotal',
        'invoice_payment_term_id',
        'partner_id',
        'currency_id',
    )
    def _compute_tax_totals(self):
        """ Computed field used for custom widget's rendering.
            Only set on invoices.
        """
        for move in self:
            # move.tax_totals = None
            if move.is_invoice(include_receipts=True):
                base_lines = move.invoice_line_ids.filtered(lambda line: line.display_type == 'product')
                base_line_values_list = [line._convert_to_tax_base_line_dict() for line in base_lines]
                if move.id:
                    # The invoice is stored so we can add the early payment discount lines directly to reduce the
                    # tax amount without touching the untaxed amount.
                    sign = -1 if move.is_inbound(include_receipts=True) else 1
                    base_line_values_list += [
                        {
                            **line._convert_to_tax_base_line_dict(),
                            'handle_price_include': False,
                            'quantity': 1.0,
                            'price_unit': sign * line.amount_currency,
                        }
                        for line in move.line_ids.filtered(lambda line: line.display_type == 'epd')
                    ]

                kwargs = {
                    'base_lines': base_line_values_list,
                    'currency': move.currency_id,
                }

                if move.id:
                    kwargs['tax_lines'] = [
                        line._convert_to_tax_line_dict()
                        for line in move.line_ids.filtered(lambda line: line.display_type == 'tax')
                    ]
                else:
                    # In case the invoice isn't yet stored, the early payment discount lines are not there. Then,
                    # we need to simulate them.
                    epd_aggregated_values = {}
                    for base_line in base_lines:
                        if not base_line.epd_needed:
                            continue
                        for grouping_dict, values in base_line.epd_needed.items():
                            epd_values = epd_aggregated_values.setdefault(grouping_dict, {'price_subtotal': 0.0})
                            epd_values['price_subtotal'] += values['price_subtotal']

                    for grouping_dict, values in epd_aggregated_values.items():
                        taxes = None
                        if grouping_dict.get('tax_ids'):
                            taxes = self.env['account.tax'].browse(grouping_dict['tax_ids'][0][2])

                        kwargs['base_lines'].append(self.env['account.tax']._convert_to_tax_base_line_dict(
                            None,
                            partner=move.partner_id,
                            currency=move.currency_id,
                            taxes=taxes,
                            price_unit=values['price_subtotal'],
                            quantity=1.0,
                            account=self.env['account.account'].browse(grouping_dict['account_id']),
                            analytic_distribution=values.get('analytic_distribution'),
                            price_subtotal=values['price_subtotal'],
                            is_refund=move.move_type in ('out_refund', 'in_refund'),
                            handle_price_include=False,
                        ))
                move.tax_totals = self.env['account.tax']._prepare_tax_totals(**kwargs)
            else:
                # Non-invoice moves don't support that field (because of multicurrency: all lines of the invoice share the same currency)
                move.tax_totals = None


    @api.depends('line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
                 'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
                 'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
                 'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
                 'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
                 'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
                 'line_ids.debit',
                 'line_ids.credit',
                 'line_ids.currency_id',
                 'line_ids.amount_currency',
                 'line_ids.amount_residual',
                 'line_ids.amount_residual_currency',
                 'line_ids.payment_id.state',
                 'line_ids.full_reconcile_id',
                 'line_ids.discount_type',
                 'line_ids.discount',
                 )
    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()
        for move in self:
            total_global_discount = 0.0
            total_discount = 0.0
            global_discount = 0.0
            global_discount_currency = 0.0
            currencies = move._get_lines_onchange_currency().currency_id

            for line in move.line_ids:
                if move.is_invoice(True):
                    if line.global_discount_amount:
                        global_discount += line.global_discount_amount
                        global_discount_currency += line.global_discount_amount
                    if line.display_type in ('product', 'rounding'):
                        total_discount += line.discount if line.discount_type == 'fixed' else line.quantity * line.price_unit * line.discount / 100.0

            if move.move_type == 'entry' or move.is_outbound():
                sign = 1
            else:
                sign = -1
            total_global_discount = -1 * sign * (global_discount_currency if len(
                currencies) == 1 else global_discount)
            total_discount += abs(total_global_discount)
            move.total_global_discount = total_global_discount
            move.total_discount = total_discount

    total_global_discount = fields.Monetary(string='Total Global Discount',
        store=True, default=0, compute='_compute_amount')
    total_discount = fields.Monetary(string='Total Discount', store=True,
        default=0, compute='_compute_amount', tracking=True)
    global_discount_type = fields.Selection([('fixed', 'Fixed'),
                                             ('percent', 'Percent')],
                                            string="Discount Type", default="percent", tracking=True)
    global_order_discount = fields.Float(string='Global Discount', store=True, tracking=True)
    is_global_discount_applied = fields.Boolean("Is Global Discount Applied", default=False)

    def action_post(self):
        """
        Override the method and create additional entries for discounts
        """
        self.delete_discount_entries()
        self.create_discount_journal_entries()
        return super().action_post()

    def button_draft(self):
        """
        Override the method and delete discount entries
        """
        res = super().button_draft()
        self.delete_discount_entries()
        return res

    def _get_discount_account(self):
        """Get Discount accounts from configurations"""
        if self.is_sale_document(include_receipts=True) and self.company_id.discount_account_invoice:
            return self.company_id.discount_account_invoice
        if self.is_purchase_document(include_receipts=True) and self.company_id.discount_account_bill:
            return self.company_id.discount_account_bill
        return None

    def delete_discount_entries(self):
        """Delete discount related entries if available"""
        for move in self:
            old_lines = move.line_ids.filtered(lambda record: record.display_type == 'global_discount')
            discount_entries = [(2, old_line.id) for old_line in old_lines]
            if discount_entries:
                move.write({
                    'invoice_line_ids': discount_entries
                })

    def create_discount_journal_entries(self):
        """Redefining the function to create new journal entries whenever
        journal discounts are provided.
        """
        for move in self:
            discount_allocation_account = move._get_discount_account()

            account_base_entries = dict()
            total_discount = 0.00
            for line in move.invoice_line_ids.filtered(lambda record: record.display_type == 'product'):
                if line.currency_id.is_zero(line.global_discount_amount) and line.currency_id.is_zero(line.discount):
                    continue

                default_discount = line.discount if line.discount_type == 'fixed' else line.currency_id.round(line.move_id.direction_sign * line.quantity * line.price_unit * line.discount/100) # Calculate default discount

                discounted_amount_currency = line.currency_id.round(
                    line.move_id.direction_sign * (line.global_discount_amount + default_discount))
                if not account_base_entries.get(str(line.account_id.id)):
                    account_base_entries[str(line.account_id.id)] = {
                        'account_id': line.account_id.id,
                        'move_id': line.move_id.id,
                        'display_type': 'global_discount',
                        'name': _("Global Discount"),
                        'amount_currency': 0.0,
                    }
                account_base_entries[str(line.account_id.id)]['amount_currency'] += discounted_amount_currency
                total_discount += discounted_amount_currency

            if not move.currency_id.is_zero(total_discount):
                account_base_entries[str(discount_allocation_account.id)] = {
                    'account_id': discount_allocation_account.id,
                    'move_id': move.id,
                    'display_type': 'global_discount',
                    'name': _("Global Discount"),
                    'amount_currency': total_discount * (-1),
                }
            if account_base_entries:
                move.write({
                    'invoice_line_ids': [(0, 0, line_value) for line_value in
                                                            account_base_entries.values()]
                })
