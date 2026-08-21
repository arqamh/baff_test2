from odoo import models, fields, api, _


class HrOvertimeTemplate(models.Model):
    _inherit = 'hr.overtime.template'

    non_working_day_start_time = fields.Float(
        string="Non Working Day Start Time",
        default=8.0,
        help="Configured start time for non-working days (public holidays, mercantile holidays, and weekends). "
             "If check-in is before this time, overtime calculation will start from this time instead of check-in time."
    )
