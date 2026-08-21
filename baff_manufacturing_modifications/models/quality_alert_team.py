from odoo import models, fields


class QualityAlertTeam(models.Model):
    _inherit = "quality.alert.team"

    notification_user_ids = fields.Many2many(
        'res.users',
        'quality_team_notification_users_rel',
        'team_id',
        'user_id',
        string='Notification Recipients',
        help='Users who will receive email notifications when quality checks pass or fail for manufacturing orders'
    )
