# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError



class StockPicking(models.Model):
    _inherit = 'stock.picking'
    _description = 'Validate Button Check Done quantity is greater than demand quantity '


    def button_validate(self):
        for rec in self:
            if self._context.get('button_validate', False) and not rec.picking_type_id.exceeded_quantity:
                for record in rec.move_ids_without_package:
                    if record.quantity_done > record.product_uom_qty:
                        raise UserError('Done quantity is greater than demand quantity')
                return super().button_validate()
            else:
                return super().button_validate()

