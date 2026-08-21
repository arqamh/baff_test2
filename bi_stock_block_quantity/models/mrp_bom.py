# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class MrpBom(models.Model):
    _inherit = 'mrp.bom'
    _description = ' Allow Validate Button Check Consumed  is greater than To Consume'

    exceeded_consumed_quantity = fields.Boolean(string=" Allow Exceeded Consumed Quantity")

