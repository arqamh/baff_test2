import logging

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
from odoo.tools import frozendict, formatLang, format_date, float_is_zero, float_compare
import functools
from contextlib import ExitStack, contextmanager
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    global_discount_percent = fields.Char("Global Discount Percentage")
    global_discount_amount = fields.Float("Global Discount Amount")
    discount_type = fields.Selection([('fixed', 'Fixed'),
                                      ('percent', 'Percent')],
                                     string="Discount Type", default="percent")
    is_global_line = fields.Boolean(string='Global Discount Line',
        help="This field is used to separate global discount line.")

    display_type = fields.Selection(
        selection=[
            ('product', 'Product'),
            ('cogs', 'Cost of Goods Sold'),
            ('tax', 'Tax'),
            ('rounding', "Rounding"),
            ('payment_term', 'Payment Term'),
            ('line_section', 'Section'),
            ('line_note', 'Note'),
            ('epd', 'Early Payment Discount'),
            ('global_discount', 'Global Discount')
        ],
        compute='_compute_display_type', store=True, readonly=False, precompute=True,
        required=True,
    )

    @api.onchange('discount_type','discount')
    def onchange_discount_validation(self):
        for line in self:
            if line.discount_type and line.discount:
                if line.discount_type == 'percent' and line.discount>100:
                    raise ValidationError("Discount can be greater than 100 percent")
                elif line.discount_type == 'fixed' and line.discount > line.price_subtotal:
                    raise ValidationError("Discount can be greater than line subtotal price")

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
    def _compute_totals(self):
        for line in self:
            if line.display_type != 'product':
                line.price_total = line.price_subtotal = False
            # Compute 'price_subtotal'.
            # line.global_discount_amount = 0
            line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            if line.discount_type and line.discount_type == 'fixed':
                line_discount_price_unit = line.price_unit - line.discount/line.quantity
            if line.global_discount_percent:
                if line.global_discount_amount:
                    line_discount_price_unit = line_discount_price_unit - line.global_discount_amount/line.quantity
                else:
                    line.global_discount_amount = line_discount_price_unit *float(line.global_discount_percent) * line.quantity
                    line_discount_price_unit = line_discount_price_unit*(1-float(line.global_discount_percent))
            subtotal = line.quantity * line_discount_price_unit

            # Compute 'price_total'.
            if line.tax_ids:
                taxes_res = line.tax_ids.compute_all(
                    line_discount_price_unit,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.partner_id,
                    is_refund=line.is_refund,
                )
                line.price_subtotal = taxes_res['total_excluded']
                line.price_total = taxes_res['total_included']
            else:
                line.price_total = line.price_subtotal = subtotal

    @api.depends('tax_ids', 'currency_id', 'partner_id', 'analytic_distribution', 'balance', 'partner_id', 'move_id.partner_id', 'price_unit')
    def _compute_all_tax(self):
        for line in self:
            sign = line.move_id.direction_sign
            if line.display_type == 'tax':
                line.compute_all_tax = {}
                line.compute_all_tax_dirty = False
                continue
            if line.display_type == 'product' and line.move_id.is_invoice(True):
                amount_currency =  line.price_unit * (1 - line.discount / 100)
                if line.discount_type and line.discount_type == 'fixed':
                    amount_currency = (line.price_unit - line.discount/line.quantity)
                if line.global_discount_percent:
                    if line.global_discount_amount:
                        amount_currency = amount_currency - line.global_discount_amount/line.quantity
                    else:
                        amount_currency = amount_currency*(1- float(line.global_discount_percent))
                amount_currency = sign * amount_currency
                handle_price_include = True
                quantity = line.quantity
            else:
                amount_currency = line.amount_currency
                handle_price_include = False
                quantity = 1
            compute_all_currency = line.tax_ids.compute_all(
                amount_currency,
                currency=line.currency_id,
                quantity=quantity,
                product=line.product_id,
                partner=line.move_id.partner_id or line.partner_id,
                is_refund=line.is_refund,
                handle_price_include=handle_price_include,
                include_caba_tags=line.move_id.always_tax_exigible,
                fixed_multiplicator=sign,
            )
            rate = line.amount_currency / line.balance if line.balance else 1
            line.compute_all_tax_dirty = True
            line.compute_all_tax = {
                frozendict({
                    'tax_repartition_line_id': tax['tax_repartition_line_id'],
                    'group_tax_id': tax['group'] and tax['group'].id or False,
                    'account_id': tax['account_id'] or line.account_id.id,
                    'currency_id': line.currency_id.id,
                    'analytic_distribution': (tax['analytic'] or not tax['use_in_tax_closing']) and line.analytic_distribution,
                    'tax_ids': [(6, 0, tax['tax_ids'])],
                    'tax_tag_ids': [(6, 0, tax['tag_ids'])],
                    'partner_id': line.move_id.partner_id.id or line.partner_id.id,
                    'move_id': line.move_id.id,
                }): {
                    'name': tax['name'],
                    'balance': tax['amount'] / rate,
                    'amount_currency': tax['amount'],
                    'tax_base_amount': tax['base'] / rate * (-1 if line.tax_tag_invert else 1),
                }
                for tax in compute_all_currency['taxes']
                if tax['amount']
            }
            if not line.tax_repartition_line_id:
                line.compute_all_tax[frozendict({'id': line.id})] = {
                    'tax_tag_ids': [(6, 0, compute_all_currency['base_tags'])],
                }
