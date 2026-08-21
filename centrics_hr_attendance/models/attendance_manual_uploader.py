import base64
from io import BytesIO
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class AttendanceManualUploader(models.Model):
    _name = 'attendance.manual.uploader'
    _description = 'Attendance Manual Uploader'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", readonly=1, store=True)
    file_upload = fields.Binary(
        string="Attendance File",
        help="Upload the attendance file."
    )
    import_configuration_id = fields.Many2one(
        'hr.attendance.import.configuration',
        string="Import Configuration",
        help="Select the attendance import configuration."
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Done')],
        string="Status",
        default='draft',
        readonly=True,
        copy=False,
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company,
        readonly=True,
        help="The company related to this record."
    )

    

    @api.model
    def create(self, vals):
        """
        Creates a new Attendance Manual Uploader record and ensures a unique sequence is
        generated and associated with it. If the sequence corresponding to the code
        'attendance.manual.uploader' doesn't exist, it will be created automatically.

        Parameters
        ----------
        vals : dict
            A dictionary of values for creating a new Attendance Manual Uploader record.

        Returns
        -------
        Model
            The newly created Attendance Manual Uploader record.
        """
        if not self.env['ir.sequence'].search([('code', '=', 'attendance.manual.uploader')], limit=1):
            self.env['ir.sequence'].create({
                'name': 'Attendance Manual Uploader',
                'code': 'attendance.manual.uploader',
                'prefix': 'AMU-',
                'padding': 5,
                'company_id': self.env.company.id,
            })
        vals['name'] = self.env['ir.sequence'].next_by_code('attendance.manual.uploader') or _('New')
        vals['company_id'] = self.env.company.id
        return super(AttendanceManualUploader, self).create(vals)

    def parse_datetime(self,value, file_type='xlsx'):
        """
        Parses a datetime string and converts it into a `datetime` object.

        This function accepts a string representation of a date and time and attempts to
        interpret it as a `datetime` object. It supports two specific formats: one
        with microseconds ("%Y-%m-%d %H:%M:%S.%f") and another without ("%Y-%m-%d %H:%M:%S").
        If the input does not match the first format, the function attempts the second one.

        Parameters
        ----------
        value : str
            A string representing the datetime to be parsed. It must follow
            one of the two accepted formats: "%Y-%m-%d %H:%M:%S.%f" or "%Y-%m-%d %H:%M:%S".

        Returns
        -------
        datetime
            A `datetime` object corresponding to the input string.

        Raises
        ------
        ValueError
            If the string does not match either of the accepted datetime formats.
        """

        if file_type == 'csv':
            # If seconds are missing, add ":00"
            if len(value.split(":")) == 2:  # Check if time is missing seconds
                value += ":00"
        if file_type == 'xls':
            # If seconds are missing, add ":00"
            if len(value.split(":")) == 2:  # Check if time is missing seconds
                value += ":00"
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M:%S.%f",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S.%f",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError as e:
                # raise ValueError(f"Invalid datet`ime format for value '{value}'") from e
                continue
        return None

    def action_import_attendance(self):
        """
        Button action to import attendance records from the uploaded file (Excel or CSV)
        based on the selected import configuration.
        """
        import os
        import pandas as pd

        self.ensure_one()

        if not self.file_upload or not self.import_configuration_id:
            raise ValidationError("Please upload a file and select an import configuration.")

        # Decode the binary file
        file_content = base64.b64decode(self.file_upload)
        file_stream = BytesIO(file_content)
        configuration = self.import_configuration_id
        file_type = configuration.file_type

        # Required fields from configuration
        field_id = configuration.field_id
        field_type = field_id.ttype
        column_name = configuration.column_name
        check_in_col = configuration.check_in_column_name
        check_out_col = configuration.check_out_column_name

        if not all([field_id, column_name, check_in_col, check_out_col]):
            raise ValidationError("The import configuration is missing required fields.")

        # Try reading the file as Excel, fallback to CSV if Excel fails
        try:
            data = pd.read_excel(file_stream, engine='openpyxl', dtype=str)
        except Exception:
            file_stream.seek(0)
            try:
                data = pd.read_csv(file_stream, dtype=str)
            except Exception as e:
                raise ValidationError(
                    "The uploaded file could not be read as either Excel or CSV. Error: %s" % str(e)
                )

        # Validate required columns
        required_columns = [column_name, check_in_col, check_out_col]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValidationError("The file is missing the following columns: %s" % ", ".join(missing_columns))

        hr_log_model = self.env["hr.attendance.manual.log"]

        for _, row in data.iterrows():
            # Convert field type and search for employee
            try:
                if field_type == 'char':
                    field_value = str(row[column_name])
                elif field_type == 'integer':
                    field_value = int(float(row[column_name]))
                elif field_type == 'float':
                    field_value = float(row[column_name])
                else:
                    field_value = str(row[column_name])  # fallback
            except Exception:
                self.message_post(
                    body=f"Invalid value for field {field_id.name}: {row[column_name]}",
                    subtype_xmlid="mail.mt_note"
                )
                continue

            employee = self.env["hr.employee"].search([(field_id.name, "=", field_value)], limit=1)

            check_in_time = self.parse_datetime(row[check_in_col], file_type=file_type)
            check_out_time = self.parse_datetime(row[check_out_col], file_type=file_type)

            if not employee:
                self.message_post(
                    body=f"No employee found for {field_id.name} = {row[column_name]}",
                    subtype_xmlid="mail.mt_note"
                )
                continue

            # Check for overlapping attendance entries
            overlapping_logs = hr_log_model.search([
                ('employee_id', '=', employee.id),
                '|',
                '&', ('checkin_time', '<=', check_in_time), ('checkout_time', '>=', check_in_time),
                '&', ('checkin_time', '<=', check_out_time), ('checkout_time', '>=', check_out_time)
            ], limit=1)

            if overlapping_logs:
                self.message_post(
                    body=(
                        f"Overlapping attendance for {employee.name}. "
                        f"Check-In: {check_in_time}, Check-Out: {check_out_time}"
                    ),
                    subtype_xmlid="mail.mt_note"
                )
                continue

            # Adjust time zone manually (hardcoded to IST here)
            if not check_in_time or not check_out_time:
                self.message_post(
                    body=f"Invalid time format for {field_id.name} = {row[column_name]}",
                    subtype_xmlid="mail.mt_note"
                )
                continue
            hr_log_model.create({
                "employee_id": employee.id,
                "checkin_time": check_in_time - relativedelta(hours=5, minutes=30),
                "checkout_time": check_out_time - relativedelta(hours=5, minutes=30),
                "state": "draft",
            })

        self.state = 'done'

