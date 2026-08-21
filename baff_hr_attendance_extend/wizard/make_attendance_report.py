from odoo import fields, models, api
from odoo.exceptions import UserError
from datetime import timedelta
from odoo.exceptions import ValidationError


class AttendanceReportWizard(models.TransientModel):
    _name = 'attendance.report.wizard'
    _description = 'Attendance Report'

    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    department_id = fields.Many2one('hr.department', string='Department')
    employee_type = fields.Selection([('all_employees', 'All Employees'), ('specific_employee', 'By Employee')], default='all_employees')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @staticmethod
    def float_to_hours_minutes(value):
        """ Convert a float value (hours in decimal form) into a string formatted as HH:MM."""
        hours = int(value)
        minutes = int(round((value - hours) * 60))
        return f"{hours}:{minutes:02d}"

    def get_attendance_report(self):
        """
        Generate an attendance report for selected employees and date range.

        - Retrieves employees based on selection (all or specific) and optional department/company filter.
        - Fetches attendance records in the given date range and groups them by employee.
        - Iterates through each day in the date range:
            - If attendance exists, converts check-in/out to user's local timezone and calculates overtime.
            - If no attendance, determines the day status:
                - Saturday/Sunday → Off day
                - Holiday → Based on resource calendar leaves (converted to user's timezone)
                - Employee leave → Based on hr.leave (converted to user's timezone)
                - Otherwise → Mark as UN-AUTHORIZED LEAVE
        - Computes total normal, double, triple overtime and holiday hours for the period.
        - Returns the data for rendering the attendance report.
        """
        if self.employee_type == 'specific_employee':
            if not self.employee_ids:
                raise UserError('Please select at least one employee.')
            employees = self.employee_ids
        else:
            domain = []
            if self.department_id:
                domain.append(('department_id', '=', self.department_id.id))
            if self.company_id:
                domain.append(('company_id', '=', self.company_id.id))
            employees = self.env['hr.employee'].search(domain)

        attendance_records = self.env['hr.attendance'].search([
            ('check_in', '>=', self.date_from),
            ('check_out', '<=', self.date_to),
            ('employee_id', 'in', employees.ids)
        ], order="employee_id, check_in")


        emp_att_map = {}
        for employee in employees:
            emp_att_map[employee.id] = attendance_records.filtered(lambda r: r.employee_id.id == employee.id)

        current_date = self.date_from
        all_dates = []
        while current_date <= self.date_to:
            all_dates.append(current_date)
            current_date += timedelta(days=1)

        attendance_lists = []

        for employee in employees:

            approved_records = emp_att_map[employee.id].filtered(lambda r: r.overtime_approval_status == 'approved')
            total_normal = sum(approved_records.mapped("normal_overtime"))
            total_double = sum(approved_records.mapped("double_overtime"))
            total_triple = sum(approved_records.mapped("triple_overtime"))
            total_holiday = sum(approved_records.mapped("holiday_hours"))

            employee_dict = {
                'employee_id': employee.name,
                'employee_epf': employee.epf_number,
                'department_id': employee.department_id.name,
                'total_normal': self.float_to_hours_minutes(total_normal),
                'total_double': self.float_to_hours_minutes(total_double),
                'total_triple': self.float_to_hours_minutes(total_triple),
                'total_holiday': self.float_to_hours_minutes(total_holiday),
                'attendance_details': [],
            }

            for day in all_dates:
                day_records = emp_att_map[employee.id].filtered(
                    lambda r: r.check_in.date() == day
                )

                if day_records:
                    for rec in day_records:
                        check_in_local = fields.Datetime.context_timestamp(self.env.user, rec.check_in)
                        check_out_local = fields.Datetime.context_timestamp(self.env.user, rec.check_out)

                        is_ot_approved = rec.overtime_approval_status == 'approved'
                        vals = {
                            'check_in_day': check_in_local.strftime('%d'),
                            'check_in_time': check_in_local.strftime('%H:%M'),
                            'check_out_day': check_out_local.strftime('%d'),
                            'check_out_time': check_out_local.strftime('%H:%M'),
                            'normal_overtime': self.float_to_hours_minutes(rec.normal_overtime if is_ot_approved else 0.0),
                            'double_overtime': self.float_to_hours_minutes(rec.double_overtime if is_ot_approved else 0.0),
                            'triple_overtime': self.float_to_hours_minutes(rec.triple_overtime if is_ot_approved else 0.0),
                            'holiday_hours': self.float_to_hours_minutes(rec.holiday_hours if is_ot_approved else 0.0),
                        }
                        employee_dict['attendance_details'].append(vals)
                else:

                    weekday = day.strftime('%A')
                    check_in_label = 'UN-AUTHORIZED LEAVE'

                    if weekday in ['Saturday']:
                        check_in_label = 'Saturday [Off day]'

                    elif weekday in ['Sunday']:
                        check_in_label = 'Sunday [Off day]'

                    else:
                        holidays = self.env['resource.calendar.leaves'].search([('time_type', '=', 'leave')])
                        matched_holiday = None

                        for holy in holidays:
                            date_from_local = fields.Datetime.context_timestamp(self.env.user, holy.date_from).date()
                            date_to_local = fields.Datetime.context_timestamp(self.env.user, holy.date_to).date()
                            if date_from_local <= day <= date_to_local:
                                matched_holiday = holy
                                break

                        if matched_holiday:
                            if matched_holiday.work_entry_type_id:
                                check_in_label = dict(
                                    matched_holiday.work_entry_type_id._fields['holiday_mapping'].selection).get(
                                    matched_holiday.work_entry_type_id.holiday_mapping
                                ) or "Holiday"
                            else:
                                check_in_label = "Holiday"

                        else:
                            leaves = self.env['hr.leave'].search([('employee_id', '=', employee.id), ('state', '=', 'validate')])
                            matched_leave = None
                            for leave in leaves:
                                # request_date_from/to are Date fields (no tz) -> use directly
                                date_from_local = leave.request_date_from
                                date_to_local = leave.request_date_to
                                if date_from_local <= day <= date_to_local:
                                    matched_leave = leave
                                    break

                            if matched_leave:
                                check_in_label = 'Leave'
                            else:
                                check_in_label = 'UN-AUTHORIZED LEAVE'

                    vals = {
                        'check_in_day': day.strftime('%d'),
                        'check_in_time': check_in_label,
                        'check_out_day': '',
                        'check_out_time': '',
                        'normal_overtime': 0.0,
                        'double_overtime': 0.0,
                        'triple_overtime': 0.0,
                        'holiday_hours': 0.0,
                    }
                    employee_dict['attendance_details'].append(vals)
            attendance_lists.append(employee_dict)
        data = {
            'form': self.read()[0],
            'attendance_records': attendance_lists,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
        return self.env.ref('baff_hr_attendance_extend.action_report_attendance').report_action(self, data=data)