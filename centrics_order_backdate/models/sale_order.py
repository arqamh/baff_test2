from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Override confirm button and add shchedule date to deliveries"""
        res = super().action_confirm()
        for record in self:
            for picking in record.picking_ids:
                picking.scheduled_date = record.date_order
                picking.date_done = record.date_order
        return res

    def _prepare_confirmation_values(self):
        """Overide method and remove dfault scheduled date from value"""
        res =  super()._prepare_confirmation_values()
        if res.get('date_order'):
            res.pop('date_order')
        return res