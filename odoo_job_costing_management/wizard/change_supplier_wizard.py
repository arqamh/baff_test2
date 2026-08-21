from odoo import fields, models, api
from datetime import datetime
from datetime import timedelta


class ChangeSupplierWizard(models.TransientModel):
    _name = 'change.supplier.wizard'

    def _current_supplier_domain(self):
        if self.env.context.get('vendors'):
            return [('id', '=', self.env.context.get('vendors'))]
        else:
            return []

    model_id = fields.Many2one('ir.model', default=lambda self: self.env['ir.model'].sudo().search([('model', '=', self._context.get('active_model'))], limit=1).id)
    record_id = fields.Integer(default=lambda self: self._context.get('active_id'))
    current_supplier_product_line = fields.One2many('supplier.product.line', 'current_supplier_id', string="Products")
    new_supplier_product_line = fields.One2many('supplier.product.line', 'new_supplier_id', string="Products")
    current_supplier_id = fields.Many2one('res.partner', string="Current Supplier", domain=_current_supplier_domain)
    new_supplier_id = fields.Many2one('res.partner', string="New Supplier")

    def change_product_supplier(self):
        """
        This method updates the supplier and costing price for each job cost line
        associated with the products in 'new_supplier_product_line'.
        """
        for line in self.new_supplier_product_line:
            if line.job_cost_line_id:
                line.job_cost_line_id.action_change_product_supplier(self.new_supplier_id, line.job_costing_price)

    @api.onchange('current_supplier_id')
    def _onchange_current_supplier_id(self):
        """OPTIMIZED: Replaced search([]).filtered() with proper domain-based query"""
        if self.current_supplier_id:
            record = self.env[self.sudo().model_id.model].sudo().search([('id', '=', self.record_id)], limit=1)
            job_cost_products = record.job_cost_line_ids.mapped('product_id.product_tmpl_id').ids if record else False
            if job_cost_products:
                # Direct search with domain - much faster than loading all records
                products = self.env['product.supplierinfo'].search([
                    ('product_tmpl_id', 'in', job_cost_products),
                    ('partner_id', '=', self.current_supplier_id.id)
                ])
                if products:
                    lines = [(5, 0, 0)]
                    for product in products:
                        lines.append((0, 0, {
                            'product_id': product.product_tmpl_id.id,
                            'job_costing_price': product.job_cost_price,
                            'lead_time': product.delay,
                        }))
                    self.current_supplier_product_line = lines

    @api.onchange('new_supplier_id')
    def _onchange_new_supplier_id(self):
        """
        This method is triggered when there is a change in the 'new_supplier_id' field.
        It updates the 'new_supplier_product_line' field with the best seller's information
        for each product line from the current supplier.
        """
        if self.new_supplier_id:
            # Initialize lines with an empty list and a command to clear existing lines
            lines = [(5, 0, 0)]
            # Loop through each product line associated with the current supplier
            for line in self.current_supplier_product_line:
                """
                The _select_seller function can be triggered in an onchange event for a purchase order line. 
                When the product, quantity, or date changes, the best seller is selected and the price is updated accordingly.
                """
                seller = line.product_id._select_seller(
                    partner_id=self.new_supplier_id,
                    quantity=None,
                    date=None,
                    uom_id=False,
                    params=False
                )
                if seller:
                    lines.append((0, 0, {
                        'product_id': seller.product_tmpl_id.product_variant_id.id,
                        'job_costing_price': seller.job_cost_price,
                        'lead_time': seller.delay,
                        'job_cost_line_id': line.job_cost_line_id,
                    }))
            self.new_supplier_product_line = lines


class SupplierProductLine(models.TransientModel):
    _name = 'supplier.product.line'

    current_supplier_id = fields.Many2one('change.supplier.wizard', string="ID")
    new_supplier_id = fields.Many2one('change.supplier.wizard', string="ID")
    product_id = fields.Many2one('product.product', string="Product")
    partner_id = fields.Many2one('res.partner', string="Vendor")
    job_costing_price = fields.Float(string="Price")
    lead_time = fields.Integer(string="Delivery Lead Time")
    job_cost_line_id = fields.Many2one('job.cost.line', string="ID")
