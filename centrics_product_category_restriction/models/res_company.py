from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    restrict_product_category_change = fields.Boolean(
        string='Restrict Product Category Change',
        help='Only authorized users can change product category'
    )
