# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError



class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    _description = 'Validate Button Check Consumed  is greater than To Consume '



    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'bom_id' not in vals:
                raise UserError('Please Select Product Bill Of Material')
        return super(MrpProduction, self).create(vals_list)

    def button_mark_done(self):
        if not self.bom_id.exceeded_consumed_quantity:
            for record in self.move_raw_ids:
                if record.quantity_done > record.product_uom_qty:
                    raise UserError('Consume Quantity Is Greater Than To Consume Quantity')
            return super(MrpProduction, self).button_mark_done()
        else:
            return super(MrpProduction, self).button_mark_done()
