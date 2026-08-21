# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta
from pytz import timezone
import pytz
import logging
from typing import Dict, Tuple
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    normal_overtime = fields.Float(string="Normal Overtime", compute="_compute_overtime", store=True)
    double_overtime = fields.Float(string="Double Overtime", compute="_compute_overtime", store=True)
    triple_overtime = fields.Float(string="Triple Overtime", compute="_compute_overtime", store=True)
    eligible_for_overtime = fields.Boolean(string="Eligible for Overtime",
                                           related='employee_id.contract_id.is_eligible_for_overtime')
    enable_inline_approval = fields.Boolean(
        string="Enable Inline Approval",
        related='employee_id.company_id.enable_inline_approval',
        store=True)
    overtime_approval_status = fields.Selection(
        [('approved', 'Approved'), ('pending', 'Pending')],
        string="Overtime Status",
        default='pending',
    )

    def _collect_applicable_deductions(self, rules, attendance_record):
        """
        Collect all unique applicable deductions from the given rules.

        Returns the total deduction in hours after checking each deduction's
        time window against the attendance record.
        """
        if not attendance_record:
            return 0.0
        seen_deduction_ids = set()
        total_deduction_minutes = 0
        for rule in rules:
            if not rule.deduction_ids:
                continue
            for deduction in rule.deduction_ids:
                if deduction.id in seen_deduction_ids:
                    continue
                seen_deduction_ids.add(deduction.id)
                if self._is_deduction_applicable(deduction, attendance_record.check_in, attendance_record.check_out):
                    total_deduction_minutes += deduction.deduction_time
        return total_deduction_minutes / 60.0

    def _apply_rules_for_duration(self, duration_hours, rules, employee, attendance_record=None, template=None):
        """
        Allocate duration into normal/double/triple overtime buckets using given rules.

        This method processes overtime rules in sequence and applies dynamic deductions
        that fall within the attendance time window.

        Parameters
        ----------
        duration_hours : float
            Total hours to allocate across rules
        rules : recordset
            hr.overtime.rule records to apply in sequence
        employee : hr.employee
            Employee record for company settings and rounding
        attendance_record : hr.attendance or None
            Attendance record used to validate deduction time windows.
            If provided, only deductions whose start_time and end_time fall
            within the attendance check-in/check-out period will be applied.
        template : hr.overtime.template or None
            The overtime template to check deduction_source configuration.

        Returns
        -------
        dict
            Dictionary with keys 'normal', 'double', 'triple' containing allocated hours
        """
        totals = {"normal": 0.0, "double": 0.0, "triple": 0.0}
        remaining = 0.0

        # When deduction_source is 'worked_hours', deduct from worked hours upfront
        # and skip per-rule deductions during allocation
        deduct_from_worked = template and template.deduction_source == 'worked_hours'
        if deduct_from_worked:
            total_deduction = self._collect_applicable_deductions(rules, attendance_record)
            duration_hours = max(0.0, duration_hours - total_deduction)

        for rule in rules:
            allocated, remaining = self.compute_overtime_allocation(
                worked_hours=duration_hours,
                rule=rule,
                remaining_unallocated_hours=remaining,
                rule_index=rules.ids.index(rule.id),
                attendance_record=attendance_record,
                skip_deductions=deduct_from_worked,
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
        return totals

    def _compute_overtime_after_checkout(self, rec, employee, template, buffer_minutes):
        """Return hours after planned checkout (+buffer) for scheduled-day OT."""
        standard_checkout = None
        check_in_user_tz = self.convert_to_user_timezone(rec.check_in)
        check_out_user_tz = self.convert_to_user_timezone(rec.check_out)
        if template.for_working_days == 'working_schedule':
            standard_checkout = self._get_standard_checkout(employee, check_in_user_tz)
        elif template.for_working_days == 'predefined':
            if not template.check_out_time:
                return 0.0
            t = self.float_to_time(template.check_out_time)
            from datetime import datetime, time as _t
            standard_checkout = datetime.combine(check_in_user_tz.date(), _t(t.hour, t.minute))
        if not standard_checkout:
            return 0.0
        std_tz = self.add_user_timezone(standard_checkout, employee)
        out_tz = self.convert_to_user_timezone(rec.check_out)
        if buffer_minutes and buffer_minutes > 0:
            from datetime import timedelta as _td
            std_tz = std_tz + _td(minutes=int(buffer_minutes))
        if check_out_user_tz >= std_tz:
            delta = (check_out_user_tz - (std_tz - + _td(minutes=int(buffer_minutes)))).total_seconds() / 3600.0
            return max(delta, 0.0)
        return 0.0

    @api.depends('check_in', 'check_out')
    def _compute_overtime(self):
        """Simple flow: public holiday → weekend → scheduled day (same & multi-day)."""
        for rec in self:
            # Reset buckets
            rec.normal_overtime = rec.double_overtime = rec.triple_overtime = 0.0
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
            check_in_date = rec.check_in.date()
            check_out_date = rec.check_out.date()
            worked_hours_full = (rec.check_out - rec.check_in).total_seconds() / 3600.0
            is_public_holiday = self._check_public_holiday(check_in_date)
            weekday_number = rec.check_in.weekday()
            is_scheduled = bool(calendar.attendance_ids.filtered(lambda a: int(a.dayofweek) == weekday_number))
            is_weekend = not is_scheduled
            # Same-day
            if check_in_date == check_out_date:
                if is_public_holiday:
                    rules = template.rule_ids.filtered(lambda r: r.apply_on == 'holidays').sorted(
                        key=lambda r: r.sequence)
                    if rules:
                        totals = self._apply_rules_for_duration(worked_hours_full, rules, employee, rec, template)
                        rec.normal_overtime, rec.double_overtime, rec.triple_overtime = totals['normal'], totals[
                            'double'], totals['triple']
                    continue
                if is_weekend:
                    rules = template.rule_ids.filtered(lambda r: r.apply_on == 'weekends').sorted(
                        key=lambda r: r.sequence)
                    if rules:
                        totals = self._apply_rules_for_duration(worked_hours_full, rules, employee, rec, template)
                        rec.normal_overtime, rec.double_overtime, rec.triple_overtime = totals['normal'], totals[
                            'double'], totals['triple']
                    continue
                rules = template.rule_ids.filtered(lambda r: r.apply_on == 'scheduled_days_check_out').sorted(
                    key=lambda r: r.sequence)
                if rules:
                    total_ot = self._compute_overtime_after_checkout(rec, employee, template, buffer_time)
                    if total_ot > 0:
                        totals = self._apply_rules_for_duration(total_ot, rules, employee, rec, template)
                        rec.normal_overtime, rec.double_overtime, rec.triple_overtime = totals['normal'], totals[
                            'double'], totals['triple']
                continue
            # Multi-day
            if check_in_date != check_out_date:
                if not template.enable_multiple_days:
                    continue
                if template.need_to_continue_from_first_day:
                    if is_public_holiday:
                        rules = template.rule_ids.filtered(lambda r: r.apply_on == 'holidays').sorted(
                            key=lambda r: r.sequence)
                        if rules:
                            totals = self._apply_rules_for_duration(worked_hours_full, rules, employee, rec, template)
                            rec.normal_overtime, rec.double_overtime, rec.triple_overtime = totals['normal'], totals[
                                'double'], totals['triple']
                        continue
                    if is_weekend:
                        rules = template.rule_ids.filtered(lambda r: r.apply_on == 'weekends').sorted(
                            key=lambda r: r.sequence)
                        if rules:
                            totals = self._apply_rules_for_duration(worked_hours_full, rules, employee, rec, template)
                            rec.normal_overtime, rec.double_overtime, rec.triple_overtime = totals['normal'], totals[
                                'double'], totals['triple']
                        continue
                    rules = template.rule_ids.filtered(lambda r: r.apply_on == 'scheduled_days_check_out').sorted(
                        key=lambda r: r.sequence)
                    if rules:
                        total_ot = self._compute_overtime_after_checkout(rec, employee, template, buffer_time)
                        if total_ot > 0:
                            totals = self._apply_rules_for_duration(total_ot, rules, employee, rec, template)
                            rec.normal_overtime, rec.double_overtime, rec.triple_overtime = totals['normal'], totals[
                                'double'], totals['triple']

    def convert_to_float_safely(self, value) -> float:
        """Return a float from any value; if value is falsy (None/False/''), return 0.0."""
        return float(value or 0.0)

    def _is_deduction_applicable(self, deduction, check_in_dt, check_out_dt):
        """
        Check if a deduction's time window falls within the attendance check-in and check-out times.

        Parameters
        ----------
        deduction : overtime.dynamic.deduction
            The deduction record with start_time and end_time
        check_in_dt : datetime
            The attendance check-in datetime
        check_out_dt : datetime
            The attendance check-out datetime

        Returns
        -------
        bool
            True if the deduction's time window is within the attendance period, False otherwise
        """
        # If no time window is defined, apply the deduction (backward compatibility)
        if not deduction.start_time or not deduction.end_time:
            return True

        # Convert attendance check-in and check-out to user timezone for comparison
        check_in_user_tz = self.convert_to_user_timezone(check_in_dt)
        check_out_user_tz = self.convert_to_user_timezone(check_out_dt)

        # Use the check-in date as the base date for deduction time window
        check_in_date = check_in_user_tz.date()

        # Convert deduction float times (e.g., 9.5 = 09:30) to datetime objects
        # Start from midnight and add the float hours
        deduction_start_dt = datetime.combine(check_in_date, datetime.min.time()) + timedelta(hours=deduction.start_time)
        deduction_end_dt = datetime.combine(check_in_date, datetime.min.time()) + timedelta(hours=deduction.end_time)

        # Localize deduction times to the employee's timezone
        employee = self.employee_id
        deduction_start_tz = self.add_user_timezone(deduction_start_dt, employee)
        deduction_end_tz = self.add_user_timezone(deduction_end_dt, employee)

        # Validate: Both deduction start and end must be within the attendance period
        # Example: If deduction is 12:00-13:00 and attendance is 09:00-18:00, it's applicable
        #          If deduction is 12:00-13:00 and attendance is 13:30-18:00, it's NOT applicable
        is_within = (deduction_start_tz >= check_in_user_tz and
                    deduction_end_tz <= check_out_user_tz)

        return is_within

    def compute_overtime_allocation(self,
                                    worked_hours: float,
                                    rule,
                                    remaining_unallocated_hours: float,
                                    rule_index: int = 0,
                                    attendance_record=None,
                                    skip_deductions: bool = False,
                                    ) -> Tuple[float, float]:
        """
        Determine how many hours this rule should allocate and return:
        (allocated_hours_for_this_rule, new_remaining_unallocated_hours).

        Rule conditions:
        - 'full_day'        : allocate the entire worked_hours to this rule.
        - 'upto_hours'      : allocate up to threshold_hours; push the leftover into remaining_unallocated_hours.
        - 'remaining_hours' : allocate whatever is currently in remaining_unallocated_hours, then zero it.

        All values are clamped to non-negative numbers. Missing fields are treated as zero.

        Parameters
        ----------
        worked_hours : float
            Total hours worked in the period
        rule : object
            The overtime rule to apply
        remaining_unallocated_hours : float
            Hours not yet allocated by previous rules
        rule_index : int
            Index of the current rule in the rules sequence
        attendance_record : hr.attendance or None
            The attendance record to validate deduction time windows against
        skip_deductions : bool
            If True, skip per-rule deductions (already deducted from worked hours upfront)

        Returns
        -------
        Tuple[float, float]
            (allocated_hours_for_this_rule, new_remaining_unallocated_hours)
        """
        safe_worked_hours = max(0.0, self.convert_to_float_safely(worked_hours))
        threshold_hours = max(0.0, self.convert_to_float_safely(getattr(rule, "threshold_hours", 0.0)))
        condition = getattr(rule, "condition", "")

        # Calculate total deduction time from dynamic deductions
        # Only apply deductions whose time window falls within the attendance period
        # This ensures deductions like "lunch break 12:00-13:00" are only applied
        # when the employee was actually present during that time window
        # Skip if deductions were already applied upfront (deduction_source == 'worked_hours')
        deduction_hours = 0.0
        if not skip_deductions and hasattr(rule, 'deduction_ids') and rule.deduction_ids and attendance_record:
            # Filter deductions: only include those whose start/end times are within attendance
            applicable_deductions = []
            for deduction in rule.deduction_ids:
                if self._is_deduction_applicable(deduction, attendance_record.check_in, attendance_record.check_out):
                    applicable_deductions.append(deduction)

            # Sum up the deduction minutes from applicable deductions only
            total_deduction_minutes = sum(deduction.deduction_time for deduction in applicable_deductions)
            deduction_hours = total_deduction_minutes / 60.0

        if condition == "full_day":
            # Take everything worked today for this rule (no change to remaining).
            allocated_hours = max(0.0, safe_worked_hours - deduction_hours)
            return allocated_hours, remaining_unallocated_hours

        if condition == "upto_hours":
            if rule_index == 0:
                # Allocate up to the configured threshold; carry the leftover forward.
                allocated_hours = min(safe_worked_hours, threshold_hours)
                allocated_hours = max(0.0, allocated_hours - deduction_hours)
                new_remaining = max(0.0, safe_worked_hours - threshold_hours)
                return allocated_hours, new_remaining
            else:
                # Allocate up to the configured threshold; carry the leftover forward.
                allocated_hours = min(remaining_unallocated_hours, threshold_hours)
                allocated_hours = max(0.0, allocated_hours - deduction_hours)
                new_remaining = max(0.0, remaining_unallocated_hours - threshold_hours)
                return allocated_hours, new_remaining

        if condition == "remaining_hours":
            # Consume whatever is left from previous 'upto_hours' allocation.
            allocated_hours = max(0.0, remaining_unallocated_hours)
            allocated_hours = max(0.0, allocated_hours - deduction_hours)
            return allocated_hours, 0.0

        # Unknown condition -> no allocation and no change to remaining.
        return 0.0, remaining_unallocated_hours

    def add_hours_to_bucket(self, overtime_totals: Dict[str, float], rule_type: str, hours_to_add: float, ) -> None:
        """Accumulate hours into the correct overtime bucket: 'normal', 'double', or 'triple'."""
        if hours_to_add <= 0.0:
            return

        if rule_type in ("normal", "double", "triple"):
            overtime_totals[rule_type] = overtime_totals.get(rule_type, 0.0) + hours_to_add
        # If rule_type is unknown, we ignore it gracefully. Replace with a ValidationError if desired.

    def _check_public_holiday(self, check_in_date):
        is_public_holiday = bool(self.env['resource.calendar.leaves'].search_count([
            ('date_from', '<=', check_in_date),
            ('date_to', '>=', check_in_date),
            ('resource_id', '=', False),
            ('work_entry_type_id.holiday_mapping', 'in', ['public', 'poya', 'religious', 'mercantile'])
        ]))
        return is_public_holiday

    @api.depends('check_in', 'check_out')
    def _get_buffer_time(self, employee):
        """
        Get the buffer time applicable for the employee based on specific configurations or global settings.
        """
        # Fetch specific buffer time for the employee's type
        specific_buffer_time = self._get_specific_buffer_time(employee.employee_type)
        if specific_buffer_time is not None:
            return specific_buffer_time

        # Fetch global buffer time if applicable
        global_buffer_time = self._get_global_buffer_time(employee)
        if global_buffer_time is not None:
            return global_buffer_time

        # Default if no configuration is found
        return 0

    def _get_specific_buffer_time(self, employee_type_key):
        """
        Retrieve specific buffer time configuration for the given employee type.
        """
        buffer_time_record = self.env['buffer.time.configuration'].search([
            ('employee_type', '=', employee_type_key)
        ], limit=1)
        return buffer_time_record.buffer_time if buffer_time_record else None

    def _get_global_buffer_time(self, employee):
        """
        Retrieve global buffer time from the employee's company configuration if allowed.
        """
        company = employee.company_id
        if company.consider_buffer_time:
            return company.buffer_time
        return None

    def _get_standard_checkout(self, employee, check_in_dt):
        """
        Determines the standard checkout time based on the employee's resource calendar
        and the provided check-in datetime. It evaluates the relevant attendance schedules
        of the employee and calculates the standard checkout time using this context.

        Parameters
        ----------
        employee : object
            The employee object containing the resource calendar with attendance schedules.
        check_in_dt : datetime
            The datetime object representing the check-in date and time.

        Returns
        -------
        datetime or None
            The datetime object representing the standard checkout time based on the
            employee's schedule. Returns None if there's no applicable resource calendar
            or attendance schedule.
        """
        calendar = employee.resource_calendar_id
        if not calendar:
            return None

        weekday = check_in_dt.weekday()
        # check_in_user_tz = self.convert_to_user_timezone(check_in_dt)
        check_date = check_in_dt.date()

        attendances = calendar.attendance_ids.filtered(lambda a: int(a.dayofweek) == weekday)
        if not attendances:
            return None

        # Find the matching schedule for the check-in hour (or earliest)
        attendances = sorted(attendances, key=lambda a: a.hour_to, reverse=True)

        for line in attendances:
            # Build datetime from the float hour_to
            checkout_time = datetime.combine(check_date, datetime.min.time()) + timedelta(hours=line.hour_to)
            return checkout_time

        return None

    def _get_template_by_job(self, job):
        """
        Retrieves an overtime template associated with a specific job.

        Searches for an overtime template that is linked to the job's position
        within the system and returns the first matching template, if any.

        Parameters
        ----------
        job : Object
            A job object whose associated overtime template is to be retrieved.

        Returns
        -------
        Object
            The first `hr.overtime.template` object matching the search criteria.
            If no matching template is found, returns an empty recordset.
        """
        return self.env['hr.overtime.template'].search([
            ('job_position_ids', 'in', job.id)
        ], limit=1)

    def _get_global_template(self):
        """
        Searches for and retrieves the global overtime template.

        This method queries the 'hr.overtime.template' model to find the template
        marked as global. It returns the first matching record, limited to one
        result, if available.

        Returns
        -------
        hr.overtime.template or None
            The first global template record if found; otherwise, None.
        """
        return self.env['hr.overtime.template'].search([
            ('is_global', '=', True)
        ], limit=1)

    def _rule_applies(self, rule, check_date, calendar):
        """
        Determines if a specific rule applies to a given date based on the provided
        calendar and rule criteria.

        Used to evaluate rule applicability against various conditions such as scheduled
        days, weekends, public holidays, or any day specified by the rule. This method
        analyzes the type of rule, checks the date against holidays, scheduled working
        days, and weekends, and returns a corresponding boolean result.

        Parameters
        ----------
        rule : object
            The rule configuration object containing the `apply_on` attribute to
            determine rule constraints. Possible options for `apply_on` are 'all',
            'scheduled_days', 'weekends', and 'holidays'.
        check_date : datetime.date
            The date to check against the given rule to determine if it satisfies the
            rule's criteria.
        calendar : object or None
            The working calendar object that defines scheduled attendance days. If
            None, the evaluation may exclude scheduled day operations.

        Returns
        -------
        bool
            True if the rule applies to the given date based on the specified criteria,
            otherwise False.
        """
        is_holiday = self.env['resource.calendar.leaves'].search_count([
            ('date_from', '<=', check_date),
            ('date_to', '>=', check_date),
            ('resource_id', '=', False)
        ]) > 0

        if rule.apply_on == 'all':
            return True
        elif rule.apply_on == 'scheduled_days':
            weekday = check_date.weekday()
            if calendar and calendar.attendance_ids.filtered(lambda a: int(a.dayofweek) == weekday):
                return not is_holiday
        elif rule.apply_on == 'weekends':
            return check_date.weekday() >= 5
        elif rule.apply_on == 'holidays':
            return is_holiday

        return False

    def float_to_time(self, time_float):
        """
        Convert a float representing time into a time object.

        This method takes a float value where the integer part represents hours
        and the fractional part represents minutes and seconds. It then converts
        it to a time object with hours, minutes, and seconds.

        Args:
            time_float (float): A float where the integer part represents hours
            and the fractional part represents minutes and seconds.

        Returns:
            time: A time object representing the hours, minutes, and seconds.

        """
        hours = int(time_float)
        minutes = int((time_float - hours) * 60)
        seconds = int((((time_float - hours) * 60) - minutes) * 60)

        return time(hours, minutes, seconds)

    def add_user_timezone(self, standard_checkout, employee_id):
        """
        Adds timezone information to a naive datetime based on the employee's timezone.

        This method takes a naive datetime object, retrieves the timezone associated
        with the specified employee, and localizes the datetime object to that timezone.
        If the employee does not have a specific timezone set, it defaults to 'Asia/Colombo'.

        Parameters:
            standard_checkout (datetime): A naive datetime object representing the checkout time.
            employee_id (object): The employee object that contains attributes, including 'tz',
                which represents the timezone of the employee or None if unspecified.

        Returns:
            datetime: The localized datetime object in the employee's timezone.
        """
        # Naive datetime (no timezone)
        naive_dt = standard_checkout

        # Get employee's timezone from record
        employee_tz = pytz.timezone(employee_id.tz or 'Asia/Colombo')

        # Properly localize the naive datetime
        localized_dt = employee_tz.localize(naive_dt)

        return localized_dt

    def convert_to_user_timezone(self, datetime_utc):
        """
        Converts a given datetime object from UTC timezone to the user's local timezone.

        This method adjusts the provided datetime object, initially assumed to be in
        the UTC timezone, to the timezone associated with the current user. If the
        user's timezone is not specified, it defaults to UTC. The datetime conversion
        retains the same moment in time but is represented in the user's local time.

        Parameters
        ----------
        datetime_utc : datetime
            The datetime object assumed to be in the UTC timezone. It must be naive
            (with no timezone information) or explicitly set to UTC.

        Returns
        -------
        datetime
            The datetime object converted to the user's local timezone. The resulting
            datetime will have the user's timezone information attached.
        """
        user_tz = self.env.user.tz or 'UTC'
        utc_timezone = timezone('UTC')
        user_timezone = timezone(user_tz)

        datetime_utc = datetime_utc.replace(tzinfo=utc_timezone)
        datetime_local = datetime_utc.astimezone(user_timezone)

        return datetime_local

    def native_datetime_to_user_timezone(self, dt):
        user = self.env.user
        user_tz = user.tz if isinstance(user.tz, str) and user.tz else 'UTC'
        user_timezone = pytz.timezone(user_tz)
        return pytz.utc.localize(dt).astimezone(user_timezone)

    def action_approve_overtime(self):
        """
        Updates the overtime approval status to 'approved' and returns a success indicator.

        This method changes the `overtime_approval_status` field of the instance to the
        value 'approved'. It indicates that the overtime request has been approved.

        Returns
        -------
        bool
            Returns `True` to indicate the action has been successfully executed.
        """
        self.overtime_approval_status = 'approved'
        return True

    def action_reset_overtime_status(self):
        """
        Resets the overtime approval status of an object.

        This method updates the `overtime_approval_status` of the calling object to
        its initial state, 'pending'. It is intended for use in workflows where the
        overtime approval process needs to be reset for re-evaluation or correction.

        Attributes
        ----------
        overtime_approval_status : str
            The current status of the overtime approval process, which will be set
            to 'pending' by this method.
        """
        self.overtime_approval_status = 'pending'

    def _round_up_time(self, time_hours, round_interval):
        """
        Rounds down the given time in hours based on the specified interval in minutes.

        Parameters
        ----------
        time_hours : float
            The time in hours to be rounded down.
        round_interval : int
            The rounding interval in minutes.

        Returns
        -------
        float
            The rounded-down time in hours.
        """

        if not self.env.company.roundup_overtime:
            return time_hours

        round_interval_hours = round_interval / 60.0
        rounded_time = round_interval_hours * (time_hours // round_interval_hours)
        return rounded_time

    def action_bulk_approve_overtime(self):
        """
        Executes the bulk approval process for overtime requests by iterating over
        the selected records and calling the respective approval method for each.

        Raises:
            ValueError: If no active IDs are provided in the context.
        """
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            records = self.browse(active_ids)
            for rec in records:
                # Custom approval logic here
                rec.action_approve_overtime()

    def action_recompute_overtime(self):
        """
        Recomputes the overtime value for each record by invoking the private method
        `_compute_overtime` for every individual record in the loop.

        Raises:
            Depends on the implementation of `_compute_overtime`. May raise any
            errors encountered during its execution.
        """
        for record in self:
            record._compute_overtime()
