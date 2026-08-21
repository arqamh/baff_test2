from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import Warning, UserError


class PurchaseRequisition(models.Model):
    _inherit = 'material.purchase.requisition'


    def _get_default_picking(self):
        # set default picking for delivery
        default_picking = self.env['stock.picking.type'].search([('default_mr_picking', '=', True)], limit=1)
        return default_picking

    custom_picking_type_id = fields.Many2one('stock.picking.type', string='Picking Type',default=_get_default_picking, copy=False)