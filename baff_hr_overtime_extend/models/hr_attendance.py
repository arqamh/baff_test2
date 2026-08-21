from datetime import datetime, time, timedelta
from pytz import timezone
import pytz
import logging
from typing import Dict, Tuple
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    holiday_hours = fields.Float(string="Holiday Hours", readonly=True, store=True)

    def _apply_rules_for_duration(self, duration_hours, rules, employee, attendance_record=None, template=None):
        """
        Applies overtime calculation rules to the given duration and returns categorized totals.

        When template.deduction_source == 'worked_hours', dynamic deductions are subtracted
        from the total worked hours BEFORE rule allocation so the rule thresholds are compared
        against the net hours. When deduction_source == 'ot_hours', the caller is responsible
        for applying deductions after this method returns.

        Arguments:
            duration_hours (float): Total hours worked to be processed.
            rules (list): A list of rules to apply for overtime calculations.
            employee (object): The employee for whom the calculation is being performed.
            attendance_record: hr.attendance record used to validate deduction time windows.
            template: hr.overtime.template used to read deduction_source configuration.

        Returns:
            dict: A dictionary containing categorized totals of hours for each overtime type.
                Keys include:
                - "normal"
                - "double"
                - "triple"
                - "holiday"
        """
        totals = {"normal": 0.0, "double": 0.0, "triple": 0.0, "holiday": 0.0}
        remaining = 0.0

        # Deduct from worked hours BEFORE rule allocation when deduction_source == 'worked_hours'
        if template and template.deduction_source == 'worked_hours' and attendance_record:
            check_in, check_out = self._get_localized_check_times(
                attendance_record.check_in, attendance_record.check_out, employee
            )
            deduction_hours = self._calculate_dynamic_deductions(rules, check_in, check_out)
            duration_hours = max(0.0, duration_hours - deduction_hours)

        for rule in rules:
            allocated, remaining = self.compute_overtime_allocation(
                worked_hours=duration_hours,
                rule=rule,
                remaining_unallocated_hours=remaining,
                rule_index=rules.ids.index(rule.id),
            )
            self.add_hours_to_bucket(
                overtime_totals=totals,
                rule_type=getattr(rule, "rule_type", ""),
                hours_to_add=allocated,
            )
        rounding = self.convert_to_float_safely(employee.company_id.roundup_overtime_interval)
        totals["normal"] = self._round_up_time(totals["normal"], rounding)
        totals["double"] = self._round_up_time(totals["double"], rounding)
        totals["triple"] = self._round_up_time(totals["triple"], rounding)
        totals["holiday"] = self._round_up_time(totals["holiday"], rounding)
        return totals

    def _check_holiday(self, check_in_date,holiday_type):
        """
        Checks if a given date is a holiday based on the specified holiday type.

        This function determines if the given `check_in_date` falls within a holiday
        period as defined by specific filters for holiday types. The relevant records
        are queried from the `resource.calendar.leaves` model.

        Parameters:
        check_in_date: datetime
            The date to be checked against the holiday periods.
        holiday_type: str
            The type of holiday to check for. Accepted values are 'public' or 'mercantile'.

        Returns:
        bool
            Returns True if the provided date falls within the specified type of holiday;
            otherwise, returns False.
        """
        filter_list = []
        if holiday_type == 'public':
            filter_list = ['public', 'poya', 'religious']
        if holiday_type == 'mercantile':
            filter_list = ['mercantile']
        is_holiday = bool(self.env['resource.calendar.leaves'].search_count([
            ('date_from', '<=', check_in_date),
            ('date_to', '>=', check_in_date),
            ('resource_id', '=', False),
            ('work_entry_type_id.holiday_mapping', 'in', filter_list)
        ]))
        return is_holiday

    def _calculate_worked_hours_with_start_time(self, check_in, check_out, configured_start_time):
        """
        Calculate worked hours considering a configured start time.

        If check_in is before the configured start time, the worked hours
        are calculated from the configured start time instead of the actual check_in time.

        Parameters:
        check_in: datetime
            The actual check-in time
        check_out: datetime
            The actual check-out time
        configured_start_time: float
            The configured start time in float format (e.g., 8.5 for 8:30 AM)

        Returns:
        float
            The calculated worked hours
        """
        if not configured_start_time:
            # If no configured start time, use the standard calculation
            return (check_out - check_in).total_seconds() / 3600.0

        # Convert float time to datetime on the same date as check_in
        hours = int(configured_start_time)
        minutes = int((configured_start_time - hours) * 60)

        # Create configured start datetime in the same timezone as check_in
        configured_start_datetime = check_in.replace(hour=hours, minute=minutes, second=0, microsecond=0)

        # If check_in is before configured start time, use configured start time
        if check_in < configured_start_datetime:
            return (check_out - configured_start_datetime).total_seconds() / 3600.0
        else:
            return (check_out - check_in).total_seconds() / 3600.0

    def _get_localized_check_times(self, check_in, check_out, employee):
        """Convert UTC check_in/check_out to the employee's timezone.

        Arguments:
            check_in (datetime): Check-in time in UTC.
            check_out (datetime): Check-out time in UTC.
            employee (recordset): The employee record whose timezone to use.

        Returns:
            tuple: (localized_check_in, localized_check_out) as naive datetimes
                   in the employee's timezone.
        """
        tz_name = employee.tz or employee.resource_calendar_id.tz or 'UTC'
        emp_tz = timezone(tz_name)
        utc = pytz.utc
        localized_check_in = utc.localize(check_in).astimezone(emp_tz).replace(tzinfo=None)
        localized_check_out = utc.localize(check_out).astimezone(emp_tz).replace(tzinfo=None)
        return localized_check_in, localized_check_out

    def _datetime_to_float_time(self, dt):
        """Convert datetime to float time (e.g., 9:30 -> 9.5)."""
        return dt.hour + dt.minute / 60.0

    def _calculate_dynamic_deductions(self, rules, check_in, check_out):
        """
        Calculate total deduction in hours from dynamic deductions.

        For each deduction in the rules, check if its [start_time, end_time]
        falls within [check_in_time, check_out_time]. If yes, add its
        deduction_time to the total.

        Arguments:
            rules (recordset): The overtime rules being applied.
            check_in (datetime): Localized check-in datetime.
            check_out (datetime): Localized check-out datetime.

        Returns:
            float: Total deduction in hours.
        """
        total_deduction_minutes = 0
        check_in_float = self._datetime_to_float_time(check_in)
        check_out_float = self._datetime_to_float_time(check_out)

        # Handle overnight shifts (check_out is next day)
        if check_out.date() > check_in.date():
            check_out_float += 24.0

        for rule in rules:
            for deduction in rule.deduction_ids:
                deduction_start = deduction.start_time
                deduction_end = deduction.end_time

                if not deduction_start and not deduction_end:
                    # No time constraints, always apply
                    total_deduction_minutes += deduction.deduction_time
                elif deduction_start is not None and deduction_end is not None:
                    # Check if deduction period is within check_in/check_out period
                    if check_in_float <= deduction_start and deduction_end <= check_out_float:
                        total_deduction_minutes += deduction.deduction_time

        return total_deduction_minutes / 60.0

    def _apply_dynamic_deductions(self, totals, deduction_hours):
        """
        Apply deduction proportionally to normal, double, and triple overtime.

        Arguments:
            totals (dict): Dictionary with 'normal', 'double', 'triple', 'holiday' keys.
            deduction_hours (float): Total hours to deduct.

        Returns:
            dict: Updated totals with deductions applied.
        """
        if deduction_hours <= 0:
            return totals

        total_ot = totals['normal'] + totals['double'] + totals['triple']
        if total_ot <= 0:
            return totals

        # Calculate remaining deduction to apply
        remaining_deduction = deduction_hours

        # Deduct from normal OT first
        if totals['normal'] > 0 and remaining_deduction > 0:
            deduct_from_normal = min(totals['normal'], remaining_deduction)
            totals['normal'] -= deduct_from_normal
            remaining_deduction -= deduct_from_normal

        # Then from double OT
        if totals['double'] > 0 and remaining_deduction > 0:
            deduct_from_double = min(totals['double'], remaining_deduction)
            totals['double'] -= deduct_from_double
            remaining_deduction -= deduct_from_double

        # Finally from triple OT
        if totals['triple'] > 0 and remaining_deduction > 0:
            deduct_from_triple = min(totals['triple'], remaining_deduction)
            totals['triple'] -= deduct_from_triple

        # Ensure no negative values
        totals['normal'] = max(0.0, totals['normal'])
        totals['double'] = max(0.0, totals['double'])
        totals['triple'] = max(0.0, totals['triple'])

        return totals

    def _apply_post_allocation_deductions(self, totals, rules, check_in, check_out, template):
        """Apply dynamic deductions after rule allocation (only when deduction_source == 'ot_hours')."""
        if template and template.deduction_source == 'worked_hours':
            return totals
        deduction_hours = self._calculate_dynamic_deductions(rules, check_in, check_out)
        return self._apply_dynamic_deductions(totals, deduction_hours)

    @api.depends('check_in', 'check_out')
    def _compute_overtime(self):
        """Simple flow: public holiday → weekend → scheduled day (same & multi-day)."""
        for rec in self:
            # Reset buckets
            rec.normal_overtime = rec.double_overtime = rec.triple_overtime = rec.holiday_hours = 0.0
            if not rec.check_in or not rec.check_out:
                continue
            employee = rec.employee_id
            contract = employee.contract_id
            if not contract:
                continue
            template = (contract.overtime_template_id
                        or self._get_template_by_job(employee.job_id)
                        or self._get_global_template())
            if not template:
                continue
            buffer_time = self._get_buffer_time(employee)
            calendar = employee.resource_calendar_id
            # Convert check_in/check_out from UTC to employee timezone
            check_in, check_out = self._get_localized_check_times(
                rec.check_in, rec.check_out, employee
            )
            check_in_date = check_in.date()
            check_out_date = check_out.date()
            worked_hours_full = (check_out - check_in).total_seconds() / 3600.0
            is_public_holiday = self._check_holiday(check_in_date, 'public')
            is_mercantile_holiday = self._check_holiday(check_in_date, 'mercantile')
            weekday_number = check_in.weekday()
            is_scheduled = bool(calendar.attendance_ids.filtered(lambda a: int(a.dayofweek) == weekday_number))
            is_weekend = not is_scheduled
            # Same-day
            if check_in_date == check_out_date:
                if is_public_holiday:
                    rules = template.rule_ids.filtered(lambda r: r.apply_on == 'public_holidays').sorted(
                        key=lambda r: r.sequence)
                    if rules:
                        wh = self._calculate_worked_hours_with_start_time(
                            check_in, check_out, template.non_working_day_start_time
                        )
                        totals = self._apply_rules_for_duration(wh, rules, employee, rec, template)
                        totals = self._apply_post_allocation_deductions(totals, rules, check_in, check_out, template)
                        rec.normal_overtime, rec.double_overtime, rec.triple_overtime, rec.holiday_hours = (
                            totals['normal'], totals['double'], totals['triple'], totals['holiday'])
                    continue
                if is_mercantile_holiday:
                    rules = template.rule_ids.filtered(lambda r: r.apply_on == 'mercantile_holidays').sorted(
                        key=lambda r: r.sequence)
                    if rules:
                        wh = self._calculate_worked_hours_with_start_time(
                            check_in, check_out, template.non_working_day_start_time
                        )
                        totals = self._apply_rules_for_duration(wh, rules, employee, rec, template)
                        totals = self._apply_post_allocation_deductions(totals, rules, check_in, check_out, template)
                        rec.normal_overtime, rec.double_overtime, rec.triple_overtime, rec.holiday_hours = (
                            totals['normal'], totals['double'], totals['triple'], totals['holiday'])
                    continue
                if is_weekend:
                    rules = template.rule_ids.filtered(lambda r: r.apply_on == 'weekends').sorted(
                        key=lambda r: r.sequence)
                    if rules:
                        wh = self._calculate_worked_hours_with_start_time(
                            check_in, check_out, template.non_working_day_start_time
                        )
                        totals = self._apply_rules_for_duration(wh, rules, employee, rec, template)
                        totals = self._apply_post_allocation_deductions(totals, rules, check_in, check_out, template)
                        rec.normal_overtime, rec.double_overtime, rec.triple_overtime, rec.holiday_hours = (
                            totals['normal'], totals['double'], totals['triple'], totals['holiday'])
                    continue
                rules = template.rule_ids.filtered(lambda r: r.apply_on == 'scheduled_days_check_out').sorted(
                    key=lambda r: r.sequence)
                if rules:
                    total_ot = self._compute_overtime_after_checkout(rec, employee, template, buffer_time)
                    if total_ot > 0:
                        totals = self._apply_rules_for_duration(total_ot, rules, employee, rec, template)
                        totals = self._apply_post_allocation_deductions(totals, rules, check_in, check_out, template)
                        rec.normal_overtime, rec.double_overtime, rec.triple_overtime, rec.holiday_hours = (
                            totals['normal'], totals['double'], totals['triple'], totals['holiday'])
                continue
            # Multi-day
            if check_in_date != check_out_date:
                if not template.enable_multiple_days:
                    continue
                if template.need_to_continue_from_first_day:
                    if is_public_holiday:
                        rules = template.rule_ids.filtered(lambda r: r.apply_on == 'public_holidays').sorted(
                            key=lambda r: r.sequence)
                        if rules:
                            wh = self._calculate_worked_hours_with_start_time(
                                check_in, check_out, template.non_working_day_start_time
                            )
                            totals = self._apply_rules_for_duration(wh, rules, employee, rec, template)
                            totals = self._apply_post_allocation_deductions(totals, rules, check_in, check_out, template)
                            rec.normal_overtime, rec.double_overtime, rec.triple_overtime, rec.holiday_hours = (
                                totals['normal'], totals['double'], totals['triple'], totals['holiday'])
                        continue
                    if is_mercantile_holiday:
                        rules = template.rule_ids.filtered(lambda r: r.apply_on == 'mercantile_holidays').sorted(
                            key=lambda r: r.sequence)
                        if rules:
                            wh = self._calculate_worked_hours_with_start_time(
                                check_in, check_out, template.non_working_day_start_time
                            )
                            totals = self._apply_rules_for_duration(wh, rules, employee, rec, template)
                            totals = self._apply_post_allocation_deductions(totals, rules, check_in, check_out, template)
                            rec.normal_overtime, rec.double_overtime, rec.triple_overtime, rec.holiday_hours = (
                                totals['normal'], totals['double'], totals['triple'], totals['holiday'])
                        continue
                    if is_weekend:
                        rules = template.rule_ids.filtered(lambda r: r.apply_on == 'weekends').sorted(
                            key=lambda r: r.sequence)
                        if rules:
                            wh = self._calculate_worked_hours_with_start_time(
                                check_in, check_out, template.non_working_day_start_time
                            )
                            totals = self._apply_rules_for_duration(wh, rules, employee, rec, template)
                            totals = self._apply_post_allocation_deductions(totals, rules, check_in, check_out, template)
                            rec.normal_overtime, rec.double_overtime, rec.triple_overtime, rec.holiday_hours = (
                                totals['normal'], totals['double'], totals['triple'], totals['holiday'])
                        continue
                    rules = template.rule_ids.filtered(lambda r: r.apply_on == 'scheduled_days_check_out').sorted(
                        key=lambda r: r.sequence)
                    if rules:
                        total_ot = self._compute_overtime_after_checkout(rec, employee, template, buffer_time)
                        if total_ot > 0:
                            totals = self._apply_rules_for_duration(total_ot, rules, employee, rec, template)
                            totals = self._apply_post_allocation_deductions(totals, rules, check_in, check_out, template)
                            rec.normal_overtime, rec.double_overtime, rec.triple_overtime, rec.holiday_hours = (
                                totals['normal'], totals['double'], totals['triple'], totals['holiday'])

    def add_hours_to_bucket(self, overtime_totals: Dict[str, float], rule_type: str, hours_to_add: float, ) -> None:
        """Accumulate hours into the correct overtime bucket: 'normal', 'double', or 'triple'."""
        if hours_to_add <= 0.0:
            return

        if rule_type in ("normal", "double", "triple", "holiday"):
            overtime_totals[rule_type] = overtime_totals.get(rule_type, 0.0) + hours_to_add
        # If rule_type is unknown, we ignore it gracefully. Replace with a ValidationError if desired.


    def _get_buffer_time(self, employee):
            """
            Override this method to implement custom buffer time logic for Ocean Voyager employee Categories
            """
            # Fetch specific buffer time for the employee's type
            specific_buffer_time = self._get_specific_buffer_time(employee.ocean_voyager_emp_category)
            if specific_buffer_time is not None:
                return specific_buffer_time

            # Fetch global buffer time if applicable
            global_buffer_time = self._get_global_buffer_time(employee)
            if global_buffer_time is not None:
                return global_buffer_time

            # Default if no configuration is found
            return 0
