from odoo import api, fields, models


class InventoryAsOnDateLine(models.TransientModel):
    _name = 'inventory.as.on.date.line'
    _description = 'Inventory As on Date Result Line'
    _rec_name = 'product_id'
    _order = 'location_id, product_id'

    wizard_id = fields.Many2one(
        'inventory.as.on.date.wizard', ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', index=True, default=lambda s: s.env.user)
    as_on_date = fields.Date(readonly=True)

    product_id = fields.Many2one(
        'product.product', string='Product', readonly=True, index=True)
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template',
        related='product_id.product_tmpl_id', store=False, readonly=True)
    category_id = fields.Many2one(
        'product.category', string='Category',
        related='product_id.categ_id', store=False, readonly=True)
    default_code = fields.Char(
        string='Internal Reference',
        related='product_id.default_code', store=False, readonly=True)
    product_name = fields.Char(
        string='Product Name',
        related='product_id.name', store=False, readonly=True)
    product_uom_id = fields.Many2one(
        'uom.uom', string='UoM',
        related='product_id.uom_id', store=False, readonly=True)

    location_id = fields.Many2one(
        'stock.location', string='Location', readonly=True, index=True)
    company_id = fields.Many2one(
        'res.company', string='Company', readonly=True)

    quantity = fields.Float(
        string='Quantity', readonly=True,
        digits='Product Unit of Measure')
    parent_category_id = fields.Many2one(
        'product.category', string='Category',
        related='product_id.categ_id.parent_id', store=False, readonly=True)
    standard_price = fields.Float(
        string='Product Value',
        related='product_id.standard_price', store=False, readonly=True,
        digits='Product Price')
    total_value = fields.Float(
        string='Total Value', compute='_compute_total_value', readonly=True,
        digits='Product Price')

    @api.depends('quantity', 'standard_price')
    def _compute_total_value(self):
        for rec in self:
            rec.total_value = rec.quantity * rec.standard_price
