from odoo import fields, models, api
from datetime import datetime
from datetime import timedelta


class AddComponentsWizard(models.TransientModel):
    _name = 'add.components.wizard'
    _description = "Add Components Wizard"

    # def _domain_user_ids_groups(self):
    #     """changed the user groups when is there a context with user group"""
    #     domain = []
    #     if self._context.get('approve_group'):
    #         domain = [('groups_id', 'in', self._context.get('approve_group'))]
    #     return domain

    bom_id = fields.Many2one('mrp.bom', string="Component", required=True)
    boat_type_id = fields.Many2one('boat.type', string="Boat Type")
    model_id = fields.Many2one('ir.model', default=lambda self: self.env['ir.model'].sudo().search(
        [('model', '=', self._context.get('active_model'))], limit=1).id)
    record_id = fields.Integer(default=lambda self: self._context.get('active_id'))
    quantity = fields.Integer(default=1, string="Quantity")

    def add_component(self):
        """function for confirm approval request"""
        record = self.env[self.sudo().model_id.model].sudo().search([('id', '=', self.record_id)], limit=1)
        res = record.action_add_component(self.bom_id, self.quantity)
        return res
