from odoo import models, fields, api, _


class Product(models.Model):
    _inherit = 'product.product'

    boq_type = fields.Selection([
        ('eqp_machine', 'Machinery / Equipment'),
        ('worker_resource', 'Worker / Resource'),
        ('work_cost_package', 'Work Cost Package'),
        ('subcontract', 'Subcontract')], 
        string='BOQ Type')


class InheritProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    job_cost_price = fields.Float(string="Job Costing Price", compute="_compute_job_costing_price")

    def _compute_job_costing_price(self):
        for record in self:
            job_cost_price = 0
            if record.company_id.vendor_price_margin:
                if record.price:
                    job_cost_price = record.price + (record.price * (record.company_id.vendor_price_margin / 100))
            else:
                job_cost_price = record.price
            record.job_cost_price = job_cost_price

    @api.onchange('price')
    def _onchange_cost_price(self):
        """Update job costing sheet when vendor price changes
        OPTIMIZED: Replaced search([]).filtered() with proper domain-based query"""
        self._compute_job_costing_price()
        for record in self:
            product = record.product_id.ids if record.product_id else record.product_tmpl_id.product_variant_ids.ids
            if not product or not record.partner_id:
                continue
            # Direct search with domain - much faster than loading all records
            job_cost_lines = record.env['job.cost.line'].search([
                ('job_costing_id.state', '=', 'draft'),
                ('job_type', '=', 'material'),
                ('partner_id', '=', record.partner_id.id),
                ('product_id', 'in', product)
            ])
            if job_cost_lines:
                job_cost_lines.write({'cost_price': record.job_cost_price})
