from odoo import models, fields, api, _
from odoo.exceptions import UserError


class InvoiceableLines(models.Model):
    _name = 'invoiceable.lines'
    _description = "Invoiceable Lines"

    order_id = fields.Many2one(comodel_name='sale.order', string="Order Reference", copy=False)
    so_order_id = fields.Many2one(comodel_name='sale.order', string="Order Reference ", copy=False)
    sequence = fields.Integer(string="Sequence", default=10)
    company_id = fields.Many2one(related='order_id.company_id', store=True, index=True, precompute=True)
    currency_id = fields.Many2one(related='order_id.currency_id', depends=['order_id.currency_id'], store=True, precompute=True)
    display_type = fields.Selection(selection=[('line_section', "Section"), ('line_note', "Note")], default=False)
    product_id = fields.Many2one(comodel_name='product.product', string="Product",
                                 change_default=True, ondelete='restrict', check_company=True, index='btree_not_null',
                                 domain="[('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    product_type = fields.Selection(related='product_id.detailed_type', depends=['product_id'])
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', depends=['product_id'])
    name = fields.Text(string="Description", store=True, readonly=False, required=True)
    product_uom_qty = fields.Float(string="Quantity", digits='Product Unit of Measure', default=1.0)
    product_uom = fields.Many2one(comodel_name='uom.uom', string="Unit of Measure", ondelete='restrict',
                                  domain="[('category_id', '=', product_uom_category_id)]")
    tax_id = fields.Many2many(comodel_name='account.tax', string="Taxes", store=True, readonly=False)
    price_unit = fields.Float(string="Unit Price", digits='Product Price')
    price_subtotal = fields.Float(string="Subtotal", compute='_compute_amount', store=True, precompute=True)
    price_tax = fields.Float(string="Total Tax", compute='_compute_amount', store=True, precompute=True)
    price_total = fields.Monetary(string="Total", compute='_compute_amount', store=True, precompute=True)
    is_downpayment = fields.Boolean(string="Downpayment", default=False)
    invoice_move_id = fields.Many2one(comodel_name='account.move', string="Related Invoice")
    hs_code = fields.Char(string='HS Code')


    @api.onchange('product_id')
    def _onchange_name(self):
        """ Assigning relevant values to invoiceable line when changing the product """
        for record in self:
            if record.product_id.display_name:
                record.name = record.product_id.display_name
                record.product_uom = record.product_id.uom_id
                record.price_unit = record.product_id.lst_price

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.order_id.partner_id,
            currency=self.order_id.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.price_unit,
            quantity=self.product_uom_qty,
            discount=None,
            price_subtotal=self.price_subtotal,
        )

    @api.depends('product_uom_qty', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            tax_results = self.env['account.tax']._compute_taxes([line._convert_to_tax_base_line_dict()])
            totals = list(tax_results['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax']

            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })
