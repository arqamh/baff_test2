from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    chatter_position = fields.Selection([
            ("manual", "Manual"),
            ("bottom", "Bottom"),
        ],
        default="manual",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["chatter_position"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["chatter_position"]
