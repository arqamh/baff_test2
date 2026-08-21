from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def open_lead(self):
        # open the lead for the current quotation
        lead = self.env['crm.lead'].search([('id', '=', self.opportunity_id.id)], limit=1)
        if lead:
            action = {
                'name': 'Lead',
                'type': 'ir.actions.act_window',
                'res_model': 'crm.lead',
                'res_id': lead.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current'
            }
            return action
