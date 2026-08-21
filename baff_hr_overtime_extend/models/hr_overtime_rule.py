from odoo import models, fields, api, _

SELECTION_RULE_TYPE = [
    ('normal', 'Normal OT'),
    ('double', 'Double OT'),
    ('triple', 'Triple OT'),
    ('holiday', 'Holiday Hours'),
]


class HrOvertimeRule(models.Model):
    _inherit = 'hr.overtime.rule'

    rule_type = fields.Selection(selection=SELECTION_RULE_TYPE)
    apply_on = fields.Selection(selection_add=[
        ('public_holidays', 'Public Holidays'),
        ('mercantile_holidays', 'Mercantile Holidays'),
        ('holidays',)
    ], tracking=True, default='all', domain="[('id', 'in', _compute_apply_on_domain())]")

