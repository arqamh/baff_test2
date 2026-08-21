import pytz
from odoo import models, fields, api, _
from odoo.exceptions import UserError



class HrAttendanceManualLog(models.Model):
    _name = 'hr.attendance.manual.log'
    _description = 'Attendance Manual Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    employee_id = fields.Many2one('hr.employee', string="Employee")
    checkin_time = fields.Datetime(string="Checkin Time")
    checkout_time = fields.Datetime(string="Checkout Time")
    state = fields.Selection([('draft', 'Draft'), ('success', 'Success'), ('failed', 'Failed')], string="State",
                             default='draft')
    note = fields.Text(string="Note")
    
    def action_process_failed_records(self):
        """Retry processing records in the failed state."""
        failed_records = self.search([('state', '=', 'failed')])
        for record in failed_records:
            try:
                if not record.employee_id or not record.checkin_time or not record.checkout_time:
                    raise ValueError("Missing mandatory fields: Employee, Check-in Time, or Check-out Time.")

                # Retry creating an attendance record in hr.attendance
                self.env['hr.attendance'].create({
                    'employee_id': record.employee_id.id,
                    'check_in': record.checkin_time,
                    'check_out': record.checkout_time,
                })

                # Update the state to 'success'
                record.state = 'success'
            except Exception as e:
                # Log the error in the note field
                record.note = str(e)
                # Add the error message to the Odoo chatter log
                record.message_post(body=f"Error: {e}", subtype_xmlid="mail.mt_note")

    def process_draft_records(self):
        """Process records in draft state and add them to hr.attendance."""
        draft_records = self.search([('state', '=', 'draft')])
        for record in draft_records:
            try:
                if not record.employee_id or not record.checkin_time or not record.checkout_time:
                    raise ValueError("Missing mandatory fields: Employee, Check-in Time, or Check-out Time.")

                # Get the user related to the employee (optional: depends on your setup)
                related_user = record.employee_id.user_id
                if related_user:
                    user_tz = related_user.tz
                    if not user_tz or not isinstance(user_tz, str):
                        msg = f"Missing or invalid timezone for employee '{record.employee_id.name}' (User: {related_user.name})"
                        record.message_post(body=msg, subtype_xmlid="mail.mt_note")
                        raise ValueError(msg)

                # Create attendance record
                self.env['hr.attendance'].create({
                    'employee_id': record.employee_id.id,
                    'check_in': record.checkin_time,
                    'check_out': record.checkout_time,
                })

                record.state = 'success'

            except Exception as e:
                record.state = 'failed'
                record.note = str(e)
                record.message_post(body=f"Error while processing record: {e}", subtype_xmlid="mail.mt_note")

    