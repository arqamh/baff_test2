from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    check_in_date = fields.Date(string="Check In Date")
    check_out_date = fields.Date(string="Check Out Date")

    @api.model
    def create(self, vals):
        if 'check_in' in vals:
            vals['check_in_date'] = fields.Date.to_date(vals['check_in'])
        if 'check_out' in vals:
            vals['check_out_date'] = fields.Date.to_date(vals['check_out'])
        return super(HrAttendance, self).create(vals)

    def write(self, vals):
        if 'check_in' in vals:
            vals['check_in_date'] = fields.Date.to_date(vals['check_in'])
        if 'check_out' in vals:
            vals['check_out_date'] = fields.Date.to_date(vals['check_out'])
        result = super(HrAttendance, self).write(vals)
        for record in self:
            if 'check_in_date' not in vals and 'check_in' in vals:
                record.check_in_date = fields.Date.to_date(record.check_in)
            if 'check_out_date' not in vals and 'check_out' in vals:
                record.check_out_date = fields.Date.to_date(record.check_out)
        return result

    def action_update_check_dates(self):
        """
        Update the check_in_date and check_out_date fields for existing records without these values.
        """
        missing_dates = self.search(
            [('check_in_date', '=', False), '|', ('check_in', '!=', False), ('check_out', '!=', False)])
        if not missing_dates:
            raise UserError(_("No records found with missing check-in or check-out dates."))
        for record in missing_dates:
            if record.check_in:
                record.check_in_date = fields.Date.to_date(record.check_in)
            if record.check_out:
                record.check_out_date = fields.Date.to_date(record.check_out)
