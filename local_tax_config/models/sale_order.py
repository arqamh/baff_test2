from odoo import fields, api, models


class InheritSaleOrder(models.Model):
    _inherit = 'sale.order'

    svat = fields.Float(string="SVAT Amount", compute='get_svat_value')
    vat_type = fields.Selection([('vat', 'VAT'), ('s_vat', 'SVAT'), ('non_vat', 'Non VAT')],
                                string="VAT Type")

    def _prepare_invoice(self):
        """ Mapping remark field with customer reference field in the invoice. """
        res = super()._prepare_invoice()
        res["vat_type"] = self.partner_id.vat_type
        journal = self.env['account.journal'].search([('vat_type', '=', self.partner_id.vat_type)], limit=1, order='sequence')
        if journal:
            res["journal_id"] = journal.id
        return res

    @api.onchange('partner_id')
    def onchange_vat_type(self):
        """ Set vat type """
        self.vat_type = self.partner_id.vat_type

    @api.depends('amount_untaxed')
    def get_svat_value(self):
        """ Get svat amount calculation """
        for line in self:
            if line.partner_id.vat_type == 's_vat':
                svat = 0
                for item in line.order_line:
                    # if_tax = item.tax_id
                    # tax = if_tax[0].amount if if_tax else 0
                    # svat += item.price_subtotal * ((tax) / 100)
                    tax_values = item.tax_id._origin.compute_all(
                        item.price_subtotal,
                        currency=item.currency_id,
                        quantity=1,
                        product=item.product_id,
                        partner=item.order_partner_id,
                        is_refund=False)
                    for tax_value in tax_values.get('taxes'):
                        if tax_value.get('amount') < 0:
                            svat += abs(tax_value.get('amount'))
                line.svat = svat
            else:
                line.svat = line.amount_tax

    @api.onchange('partner_id')
    def odoo_onchange_partner_id(self):
        """ Calling the order line function to compute """
        self.order_line._compute_tax_id()


class InheritSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _compute_tax_id(self):
        for line in self:
            """ Overriding core function to set the taxes based on partner vat type """
            fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.taxes_id.filtered(lambda r: not line.company_id or r.company_id == line.company_id)
            if line.order_id.partner_id:
                if line.order_id.partner_id.vat_type in ['non_vat', 'vat']:
                    taxes = taxes.filtered(lambda x: x.vat_type == 'vat')
                else:
                    taxes = taxes.filtered(lambda x: x.vat_type == 's_vat')
            line.tax_id = fpos.map_tax(taxes, line.product_id, line.order_id.partner_shipping_id) if fpos else taxes
