from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mpr_default_picking_type = fields.Many2one(
        'stock.picking.type',
        related='company_id.default_picking_type',
        string='Default Picking Type',
        readonly=False,
    )
    procurement_notification_user_ids = fields.Many2many(
        related='company_id.procurement_notification_user_ids',
        string='Procurement Notification Users',
        readonly=False,
    )
    procurement_notification_emails = fields.Char(
        related='company_id.procurement_notification_emails',
        string='Procurement Notification Emails',
        readonly=False,
    )
    asset_procurement_team_emails = fields.Char(
        related='company_id.asset_procurement_team_emails',
        string='Asset Procurement Team Emails',
        readonly=False,
    )
