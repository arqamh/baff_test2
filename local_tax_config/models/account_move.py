from odoo import fields, api, models


class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    svat = fields.Float(string="SVAT Amount", compute='get_svat_value')
    vat_type = fields.Selection([('vat', 'VAT'), ('s_vat', 'SVAT'), ('non_vat', 'Non VAT')],
                                string="VAT Type", default='vat')

    @api.depends('amount_untaxed')
    def get_svat_value(self):
        """ Get svat amount calculation """
        for line in self:
            if line.partner_id.vat_type == 's_vat':
                svat = 0
                for item in line.invoice_line_ids:
                    # if_tax = item.tax_ids
                    # tax = if_tax[0].amount if if_tax else 0
                    # svat += item.price_subtotal * ((tax) / 100)
                    tax_values = item.tax_ids._origin.compute_all(
                        item.price_subtotal,
                        currency=item.company_currency_id,
                        quantity=1,
                        product=item.product_id,
                        partner=item.partner_id,
                        is_refund=line.move_type in ('out_refund', 'in_refund'))
                    for tax_value in tax_values.get('taxes'):
                        if tax_value.get('amount') < 0:
                            svat += abs(tax_value.get('amount'))
                line.svat = svat
            else:
                line.svat = line.amount_tax

    @api.onchange('partner_id')
    def odoo_onchange_partner_id(self):
        """ Calling the order line function to compute """
        self.vat_type = self.partner_id.vat_type

        if self.vat_type and self.suitable_journal_ids:
            journal_id = self.journal_id.search([('id', 'in', self.suitable_journal_ids.ids),
                                                 ('vat_type', '=', self.vat_type)], limit=1)
            if journal_id:
                self.journal_id = journal_id.id
                self._onchange_journal_id()
            else:
                non_journal_id = self.journal_id.search([('id', 'in', self.suitable_journal_ids.ids),
                                                         ('vat_type', '=', False)], limit=1)
                self.journal_id = non_journal_id.id if non_journal_id else False
                self._onchange_journal_id()

        for line in self.invoice_line_ids:
            line._compute_name()

    @api.depends('company_id', 'invoice_filter_type_domain', 'partner_id')
    def _compute_suitable_journal_ids(self):
        """ Overriding core method to vat type into the domain when setting journals in the invoice """
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company_id = m.company_id.id or self.env.company.id
            domain = [('company_id', '=', company_id), ('type', '=', journal_type), '|', ('vat_type', '=', m.vat_type),
                      ('vat_type', '=', False)]
            m.suitable_journal_ids = self.env['account.journal'].search(domain)
            # m._onchange_journal()


class InheritAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_computed_taxes(self):
        """ Overriding core method to set taxes in product lines based on customer vat types
        and customer taxes in product """
        self.ensure_one()

        if self.move_id.is_sale_document(include_receipts=True):
            # Out invoice.
            if self.product_id.taxes_id:
                tax_ids = self.product_id.taxes_id.filtered(lambda tax: tax.company_id == self.move_id.company_id)
                if self.move_id.partner_id:
                    if self.move_id.partner_id.vat_type in ['non_vat', 'vat']:
                        tax_ids = tax_ids.filtered(lambda x: x.vat_type == 'vat')
                    else:
                        tax_ids = tax_ids.filtered(lambda x: x.vat_type == 's_vat')
            else:
                tax_ids = self.account_id.tax_ids.filtered(lambda tax: tax.type_tax_use == 'sale')
            if not tax_ids and self.display_type == 'product':
                tax_ids = self.move_id.company_id.account_sale_tax_id
        elif self.move_id.is_purchase_document(include_receipts=True):
            # In invoice.
            if self.product_id.supplier_taxes_id:
                tax_ids = self.product_id.supplier_taxes_id.filtered(
                    lambda tax: tax.company_id == self.move_id.company_id)
                if self.move_id.partner_id:
                    if self.move_id.partner_id.vat_type in ['non_vat', 'vat']:
                        tax_ids = tax_ids.filtered(lambda x: x.vat_type == 'vat')
                    else:
                        tax_ids = tax_ids.filtered(lambda x: x.vat_type == 's_vat')
            else:
                tax_ids = self.account_id.tax_ids.filtered(lambda tax: tax.type_tax_use == 'purchase')
            if not tax_ids and self.display_type == 'product':
                tax_ids = self.move_id.company_id.account_purchase_tax_id
        else:
            # Miscellaneous operation.
            tax_ids = self.account_id.tax_ids

        if self.company_id and tax_ids:
            tax_ids = tax_ids.filtered(lambda tax: tax.company_id == self.company_id)

        if tax_ids and self.move_id.fiscal_position_id:
            tax_ids = self.move_id.fiscal_position_id.map_tax(tax_ids)

        return tax_ids
