from datetime import datetime, timedelta
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'overtime_calculation')
class TestHrAttendanceOvertimeSameDay(TransactionCase):
    """
    Test cases for same-day overtime calculation with non-working day start time configuration.

    These tests verify that the overtime calculation correctly applies the configured
    non_working_day_start_time for public holidays, mercantile holidays, and weekends.
    """

    def setUp(self):
        super(TestHrAttendanceOvertimeSameDay, self).setUp()

        # Create a company
        self.company = self.env['res.company'].create({
            'name': 'Test Company',
            'roundup_overtime_interval': 0.25,  # 15 minutes
        })

        # Create a work entry type for public holiday
        self.work_entry_type_public = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday',
            'code': 'PUBLIC_HOLIDAY',
            'holiday_mapping': 'public',
        })

        # Create a work entry type for mercantile holiday
        self.work_entry_type_mercantile = self.env['hr.work.entry.type'].create({
            'name': 'Mercantile Holiday',
            'code': 'MERCANTILE_HOLIDAY',
            'holiday_mapping': 'mercantile',
        })

        # Create a resource calendar (standard work week: Mon-Fri)
        self.calendar = self.env['resource.calendar'].create({
            'name': 'Standard 40h/week',
            'company_id': self.company.id,
        })

        # Add attendance lines for Monday to Friday (0-4)
        for day in range(5):
            self.env['resource.calendar.attendance'].create({
                'name': f'Day {day}',
                'dayofweek': str(day),
                'hour_from': 9.0,
                'hour_to': 17.0,
                'calendar_id': self.calendar.id,
            })

        # Create overtime template with non_working_day_start_time set to 8:00 AM
        self.overtime_template = self.env['hr.overtime.template'].create({
            'name': 'Test Overtime Template',
            'is_global': True,
            'for_working_days': 'working_schedule',
            'non_working_day_start_time': 8.0,  # 8:00 AM
            'company_id': self.company.id,
            'state': 'draft',
        })

        # Create overtime rules for public holidays
        self.rule_public_holiday = self.env['hr.overtime.rule'].create({
            'name': 'Public Holiday Rule',
            'template_id': self.overtime_template.id,
            'apply_on': 'public_holidays',
            'rule_type': 'holiday',
            'condition': 'after_hours',
            'threshold_hours': 0.0,
            'sequence': 1,
        })

        # Create overtime rules for mercantile holidays
        self.rule_mercantile_holiday = self.env['hr.overtime.rule'].create({
            'name': 'Mercantile Holiday Rule',
            'template_id': self.overtime_template.id,
            'apply_on': 'mercantile_holidays',
            'rule_type': 'double',
            'condition': 'after_hours',
            'threshold_hours': 0.0,
            'sequence': 1,
        })

        # Create overtime rules for weekends
        self.rule_weekend = self.env['hr.overtime.rule'].create({
            'name': 'Weekend Rule',
            'template_id': self.overtime_template.id,
            'apply_on': 'weekends',
            'rule_type': 'triple',
            'condition': 'after_hours',
            'threshold_hours': 0.0,
            'sequence': 1,
        })

        # Create an employee
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'company_id': self.company.id,
            'resource_calendar_id': self.calendar.id,
        })

        # Create a contract for the employee
        self.contract = self.env['hr.contract'].create({
            'name': 'Test Contract',
            'employee_id': self.employee.id,
            'wage': 5000.0,
            'state': 'open',
            'date_start': datetime.now().date() - timedelta(days=365),
            'overtime_template_id': self.overtime_template.id,
        })

    def test_public_holiday_checkin_before_start_time(self):
        """
        Test overtime calculation for public holiday when check-in is before configured start time.

        Scenario:
        - Public holiday on a Monday
        - Configured start time: 8:00 AM
        - Check-in: 7:00 AM
        - Check-out: 5:00 PM (17:00)
        - Expected worked hours: 9 hours (from 8:00 AM to 5:00 PM)
        """
        # Create a public holiday for testing (e.g., 2025-12-01 - Monday)
        test_date = datetime(2025, 12, 1, 0, 0, 0)
        self.env['resource.calendar.leaves'].create({
            'name': 'Test Public Holiday',
            'date_from': test_date,
            'date_to': test_date + timedelta(hours=23, minutes=59),
            'resource_id': False,
            'calendar_id': self.calendar.id,
            'work_entry_type_id': self.work_entry_type_public.id,
        })

        # Create attendance with check-in before start time
        check_in = datetime(2025, 12, 1, 7, 0, 0)  # 7:00 AM
        check_out = datetime(2025, 12, 1, 17, 0, 0)  # 5:00 PM

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
        })

        # Verify the overtime calculation
        # Expected: 9 hours (from 8:00 AM to 5:00 PM, not from 7:00 AM)
        self.assertEqual(attendance.holiday_hours, 9.0,
                        "Holiday hours should be 9.0 (calculated from 8:00 AM, not 7:00 AM)")

    def test_public_holiday_checkin_after_start_time(self):
        """
        Test overtime calculation for public holiday when check-in is after configured start time.

        Scenario:
        - Public holiday on a Monday
        - Configured start time: 8:00 AM
        - Check-in: 9:00 AM
        - Check-out: 5:00 PM (17:00)
        - Expected worked hours: 8 hours (from 9:00 AM to 5:00 PM)
        """
        # Create a public holiday for testing (e.g., 2025-12-02 - Tuesday)
        test_date = datetime(2025, 12, 2, 0, 0, 0)
        self.env['resource.calendar.leaves'].create({
            'name': 'Test Public Holiday 2',
            'date_from': test_date,
            'date_to': test_date + timedelta(hours=23, minutes=59),
            'resource_id': False,
            'calendar_id': self.calendar.id,
            'work_entry_type_id': self.work_entry_type_public.id,
        })

        # Create attendance with check-in after start time
        check_in = datetime(2025, 12, 2, 9, 0, 0)  # 9:00 AM
        check_out = datetime(2025, 12, 2, 17, 0, 0)  # 5:00 PM

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
        })

        # Verify the overtime calculation
        # Expected: 8 hours (from 9:00 AM to 5:00 PM)
        self.assertEqual(attendance.holiday_hours, 8.0,
                        "Holiday hours should be 8.0 (calculated from 9:00 AM)")

    def test_mercantile_holiday_checkin_before_start_time(self):
        """
        Test overtime calculation for mercantile holiday when check-in is before configured start time.

        Scenario:
        - Mercantile holiday on a Wednesday
        - Configured start time: 8:00 AM
        - Check-in: 6:30 AM
        - Check-out: 4:00 PM (16:00)
        - Expected worked hours: 8 hours (from 8:00 AM to 4:00 PM)
        """
        # Create a mercantile holiday for testing (e.g., 2025-12-03 - Wednesday)
        test_date = datetime(2025, 12, 3, 0, 0, 0)
        self.env['resource.calendar.leaves'].create({
            'name': 'Test Mercantile Holiday',
            'date_from': test_date,
            'date_to': test_date + timedelta(hours=23, minutes=59),
            'resource_id': False,
            'calendar_id': self.calendar.id,
            'work_entry_type_id': self.work_entry_type_mercantile.id,
        })

        # Create attendance with check-in before start time
        check_in = datetime(2025, 12, 3, 6, 30, 0)  # 6:30 AM
        check_out = datetime(2025, 12, 3, 16, 0, 0)  # 4:00 PM

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
        })

        # Verify the overtime calculation
        # Expected: 8 hours in double_overtime (from 8:00 AM to 4:00 PM)
        self.assertEqual(attendance.double_overtime, 8.0,
                        "Double overtime should be 8.0 (calculated from 8:00 AM, not 6:30 AM)")

    def test_mercantile_holiday_checkin_after_start_time(self):
        """
        Test overtime calculation for mercantile holiday when check-in is after configured start time.

        Scenario:
        - Mercantile holiday on a Thursday
        - Configured start time: 8:00 AM
        - Check-in: 10:00 AM
        - Check-out: 6:00 PM (18:00)
        - Expected worked hours: 8 hours (from 10:00 AM to 6:00 PM)
        """
        # Create a mercantile holiday for testing (e.g., 2025-12-04 - Thursday)
        test_date = datetime(2025, 12, 4, 0, 0, 0)
        self.env['resource.calendar.leaves'].create({
            'name': 'Test Mercantile Holiday 2',
            'date_from': test_date,
            'date_to': test_date + timedelta(hours=23, minutes=59),
            'resource_id': False,
            'calendar_id': self.calendar.id,
            'work_entry_type_id': self.work_entry_type_mercantile.id,
        })

        # Create attendance with check-in after start time
        check_in = datetime(2025, 12, 4, 10, 0, 0)  # 10:00 AM
        check_out = datetime(2025, 12, 4, 18, 0, 0)  # 6:00 PM

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
        })

        # Verify the overtime calculation
        # Expected: 8 hours in double_overtime (from 10:00 AM to 6:00 PM)
        self.assertEqual(attendance.double_overtime, 8.0,
                        "Double overtime should be 8.0 (calculated from 10:00 AM)")

    def test_weekend_checkin_before_start_time(self):
        """
        Test overtime calculation for weekend when check-in is before configured start time.

        Scenario:
        - Weekend (Saturday)
        - Configured start time: 8:00 AM
        - Check-in: 7:30 AM
        - Check-out: 3:30 PM (15:30)
        - Expected worked hours: 7.5 hours (from 8:00 AM to 3:30 PM)
        """
        # Create attendance on weekend (Saturday - day 5)
        check_in = datetime(2025, 12, 6, 7, 30, 0)  # 7:30 AM on Saturday
        check_out = datetime(2025, 12, 6, 15, 30, 0)  # 3:30 PM

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
        })

        # Verify the overtime calculation
        # Expected: 7.5 hours in triple_overtime (from 8:00 AM to 3:30 PM, not from 7:30 AM)
        self.assertEqual(attendance.triple_overtime, 7.5,
                        "Triple overtime should be 7.5 (calculated from 8:00 AM, not 7:30 AM)")

    def test_weekend_checkin_after_start_time(self):
        """
        Test overtime calculation for weekend when check-in is after configured start time.

        Scenario:
        - Weekend (Sunday)
        - Configured start time: 8:00 AM
        - Check-in: 11:00 AM
        - Check-out: 7:00 PM (19:00)
        - Expected worked hours: 8 hours (from 11:00 AM to 7:00 PM)
        """
        # Create attendance on weekend (Sunday - day 6)
        check_in = datetime(2025, 12, 7, 11, 0, 0)  # 11:00 AM on Sunday
        check_out = datetime(2025, 12, 7, 19, 0, 0)  # 7:00 PM

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
        })

        # Verify the overtime calculation
        # Expected: 8 hours in triple_overtime (from 11:00 AM to 7:00 PM)
        self.assertEqual(attendance.triple_overtime, 8.0,
                        "Triple overtime should be 8.0 (calculated from 11:00 AM)")

    def test_no_configured_start_time(self):
        """
        Test overtime calculation when no start time is configured (default behavior).

        Scenario:
        - Weekend (Saturday)
        - Configured start time: 0.0 (not set)
        - Check-in: 7:00 AM
        - Check-out: 5:00 PM (17:00)
        - Expected worked hours: 10 hours (from 7:00 AM to 5:00 PM)
        """
        # Update template to have no configured start time
        self.overtime_template.write({'non_working_day_start_time': 0.0})

        # Create attendance on weekend (Saturday - day 5)
        check_in = datetime(2025, 12, 13, 7, 0, 0)  # 7:00 AM on Saturday
        check_out = datetime(2025, 12, 13, 17, 0, 0)  # 5:00 PM

        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
        })

        # Verify the overtime calculation
        # Expected: 10 hours in triple_overtime (from 7:00 AM to 5:00 PM)
        self.assertEqual(attendance.triple_overtime, 10.0,
                        "Triple overtime should be 10.0 (calculated from actual check-in time)")
