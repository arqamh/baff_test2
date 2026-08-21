# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################

import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def remove_global_discount(self):
        if self.order_line:
            self.order_line.write({
                'global_discount_percent': '',
                'global_discount_amount':0
            })
            self.is_global_discount_applied = False
            self.global_order_discount = 0
            self.order_line._compute_amount()

    def action_update_discount(self):
        if self.order_line:
            if not self.global_order_discount:
                self.order_line.write({
                    'global_discount_percent': '',
                    'global_discount_amount':0

                })
                self.is_global_discount_applied = False
            elif self.global_discount_type == 'percent':
                if self.global_order_discount >100 or self.global_order_discount <0:
                    raise ValidationError("Please enter the valid discount")
                self.order_line.write({
                    'global_discount_percent':str(self.global_order_discount/100),
                    'global_discount_amount':0

                })
                self.is_global_discount_applied = True
            else:
                total_amount = 0
                # for line in self.order_line.filtered(lambda line: not line.product_id.categ_id.restrict_global_discount): # Removed due to not configurations in the product category
                for line in self.order_line:
                    discount_type = ''
                    discount_type = line.discount_type
                    quantity = line.product_qty
                    if discount_type == 'fixed':
                        line_discount_price_unit = line.price_unit * line.product_qty - line.discount
                        quantity = 1.0
                    else:
                        line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
                    total_amount += line_discount_price_unit*quantity
                if total_amount < self.global_order_discount:
                    raise ValidationError("Discount can't be greater than the order amount")
                self.is_global_discount_applied = True
                self.order_line.write({
                    'global_discount_percent': str(self.global_order_discount/total_amount),
                    'global_discount_amount':0
                })
            self.order_line._compute_amount()

    @api.depends('order_line.price_total', 'order_line.discount_type',
                 'order_line.discount')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = total_discount = total_global_discount = 0.0

            for line in order.order_line:
                line._compute_amount()
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                if line.discount_type == 'fixed':
                    total_discount += line.discount
                else:
                    total_discount += line.price_unit * line.product_qty * (
                        (line.discount or 0.0) / 100.0)
                if line.global_discount_amount:
                    total_global_discount += line.global_discount_amount
    

            IrConfigPrmtrSudo = self.env['ir.config_parameter'].sudo()
            discTax = IrConfigPrmtrSudo.get_param('account.global_discount_tax')
            if not discTax:
                discTax = 'untax'
            total = amount_untaxed
            if discTax == 'taxed':
                total +=  amount_tax
            total_discount += total_global_discount

            if discTax != 'taxed':
                total += amount_tax

            currency = order.currency_id or order.partner_id.property_purchase_currency_id or self.env.company.currency_id
            order.update({
                'amount_untaxed': currency.round(amount_untaxed),
                'amount_tax': currency.round(amount_tax),
                'amount_total': currency.round(total),
                'total_global_discount': currency.round(total_global_discount),
                'total_discount': currency.round(total_discount),
            })

    is_global_discount_applied = fields.Boolean(string="Is Global Discount Applied", default=False)
    total_global_discount = fields.Monetary(string='Total Global Discount', store=True,
                                            readonly=True, compute='_amount_all')
    total_discount = fields.Monetary(string='Total Discount', store=True, readonly=True,
                                     compute='_amount_all', tracking=True)
    global_discount_type = fields.Selection(
        [('fixed', 'Fixed'), ('percent', 'Percent')],
        string="Discount Type",
        default="percent",
        help="If global discount type 'Fixed' has been applied then no partial invoice will be generated for this order.")
    global_order_discount = fields.Float(string='Global Discount', store=True, tracking=True)

    def _prepare_invoice(self):
        self.ensure_one()
        if self.global_order_discount and not self.env.company.discount_account_bill:
            raise UserError(
                _("Global Discount!\nPlease first set account for global discount in purchase setting."))
        global_order_discount = self.global_order_discount
        # For fixed global discount with partial invoicing, scale the discount
        # proportionally based on the value of lines being invoiced vs total order value.
        if global_order_discount and self.global_discount_type == 'fixed':
            total_order_value = 0.0
            invoiceable_value = 0.0
            for line in self.order_line:
                if line.discount_type == 'fixed':
                    line_value = line.price_unit * line.product_qty - line.discount
                else:
                    line_value = line.price_unit * (1 - (line.discount or 0.0) / 100.0) * line.product_qty
                total_order_value += line_value
                if line.qty_to_invoice > 0:
                    invoice_ratio = line.qty_to_invoice / line.product_qty if line.product_qty else 0.0
                    invoiceable_value += line_value * invoice_ratio
            if total_order_value:
                global_order_discount = self.currency_id.round(
                    global_order_discount * invoiceable_value / total_order_value)
        vals = super(PurchaseOrder, self)._prepare_invoice()
        vals.update({
            'global_discount_type': self.global_discount_type,
            'global_order_discount': global_order_discount,
        })
        return vals

    def action_view_invoice(self, invoices=False):
        moves = super(PurchaseOrder, self).action_view_invoice(invoices)
        if invoices:
            invoices._compute_amount()
            invoices.with_context({'check_move_validity':False}).action_update_discount()
        return moves


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.depends('price_unit', 'discount_type', 'discount', 'taxes_id', 'product_qty')
    def _get_line_subtotal(self):
        for line in self:
            if line.discount_type == 'fixed':
                price = line.price_unit * line.product_qty - (line.discount or 0.0)
                quantity = 1
            else:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                quantity = line.product_qty
            taxes = line.taxes_id.compute_all(price, line.order_id.currency_id, quantity,
                                              product=line.product_id, partner=line.order_id.partner_id)
            _logger.info("========%r",taxes)
            line.line_sub_total = taxes['total_excluded']

    global_discount_percent = fields.Char("Global Discount Percentage")
    global_discount_amount = fields.Float("Global Discount Amount")
    line_sub_total = fields.Monetary(compute='_get_line_subtotal',
                                     string='Line Subtotal', readonly=True, store=True)
    discount = fields.Float(string='Discount', digits='Discount', default=0.0)
    discount_type = fields.Selection(
        [('fixed', 'Fixed'), ('percent', 'Percent')],
        string="Discount Type",
        default="percent")

    @api.onchange('discount','discount_type')
    def onchange_line_discount(self):
        for line in self:
            if line.discount_type and line.discount:
                if line.discount_type == 'percent' and line.discount>100:
                    raise ValidationError("Discount can be greater than 100 percent")
                elif line.discount_type == 'fixed' and line.discount > line.price_subtotal:
                    raise ValidationError("Discount can be greater than line subtotal price")
                
    @api.onchange('product_uom_qty','discount', 'price_unit', 'tax_id')
    def onchange_update_line_discount(self):
        for line in self:
            if line.discount:
                line._compute_amount()
                if line.order_id.is_global_discount_applied:
                    line.order_id.action_update_discount()            
                
    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        return super(PurchaseOrderLine, self)._compute_amount()

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.
        :return: A python dictionary.
        """
        self.ensure_one()
        quantity = 1.0
        if self.discount_type == 'fixed':
            price = self.price_unit * self.product_qty - (self.discount or 0.0)
        else:
            price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
            quantity = self.product_qty
        # if self.global_discount_percent and not self.product_id.categ_id.restrict_global_discount: # Removed this configrations not in the category
        if self.global_discount_percent:
                self.global_discount_amount = price*float(self.global_discount_percent)*quantity
                price = price - price*float(self.global_discount_percent)    
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.order_id.partner_id,
            currency=self.order_id.currency_id,
            product=self.product_id,
            taxes=self.taxes_id,
            price_unit=price,
            quantity=quantity,
            price_subtotal=self.price_subtotal,
        )


    def _prepare_compute_all_values(self):
        vals = super(PurchaseOrderLine, self)._prepare_compute_all_values()
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        quantity = self.product_qty
        if self.discount_type == 'fixed':
            quantity = 1.0
            price = self.price_unit * self.product_qty - (self.discount or 0.0)
        vals.update({
            'price_unit': price,
            'quantity': quantity,
        })
        return vals

    def _prepare_account_move_line(self, move=False):
        self.ensure_one()
        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move=move)
        res.update({
            'discount_type': self.discount_type,
            'discount': self.discount,
        })
        return res
