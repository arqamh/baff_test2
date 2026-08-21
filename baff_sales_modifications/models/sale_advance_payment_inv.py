from odoo import fields, models, api


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'


    def _create_invoices(self, sale_orders):
        ''' Create Invoiceable lines in Invoice from Sales Orders Invoiceable lines'''

        invoices = super()._create_invoices(sale_orders)

        invoiceable_lines = self.env['invoiceable.lines'].search([('product_id', '!=', False),
                                                                  ('so_order_id', 'in', self.sale_order_ids.ids)])

        for invoice in invoices:
            invoice_lines = []
            for line in invoiceable_lines:
                invoice_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'price_unit': line.price_unit,
                    'tax_id': line.tax_id,
                    'price_subtotal': line.price_subtotal,
                }))
            invoice.write({
                'invoiceable_line_ids': invoice_lines,
            })
        return invoices
