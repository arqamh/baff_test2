from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'


    def button_confirm(self):
        """Override confirm button and add shchedule date to deliveries"""
        res = super().button_confirm()
        for record in self:
            if record.picking_ids:
                for picking in record.picking_ids:
                    picking.scheduled_date = record.date_planned
        return res