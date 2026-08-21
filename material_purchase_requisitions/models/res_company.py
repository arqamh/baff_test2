from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    default_picking_type = fields.Many2one('stock.picking.type', string='Default Picking Type')
    procurement_notification_user_ids = fields.Many2many(
        'res.users',
        'mpr_procurement_notify_user_rel',
        'company_id',
        'user_id',
        string='Procurement Notification Users',
        help="Internal users who should be notified when an Asset Purchase requisition is converted to an RFQ/PO.",
    )
    procurement_notification_emails = fields.Char(
        string='Procurement Notification Emails',
        help="Additional comma-separated email addresses that should be notified when an Asset Purchase requisition "
             "is converted to an RFQ/PO.",
    )
    asset_procurement_team_emails = fields.Char(
        string='Asset Procurement Team Emails',
        help="Legacy alias — kept so previously-saved views resolve. "
             "Use 'Procurement Notification Emails' in the Settings UI.",
    )
