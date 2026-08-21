from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_asset_purchase = fields.Boolean(string='Asset Purchase', copy=False, tracking=True)
    asset_location_id = fields.Many2one('stock.location', string='Asset Location', copy=False, tracking=True,
                                        domain="[('usage', '=', 'internal')]",
                                        help="Location where the purchased asset will be delivered/installed.")
    custom_requisition_id = fields.Many2one('material.purchase.requisition', string='Material Requisition',
                                            copy=False)
