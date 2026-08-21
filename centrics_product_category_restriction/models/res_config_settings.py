# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    restrict_product_category_change = fields.Boolean(
        related='company_id.restrict_product_category_change',
        readonly=False,
        string='Restrict Product Category Change',
        help='Only authorized users can change product category'
    )
