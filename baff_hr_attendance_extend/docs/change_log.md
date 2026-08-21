## Date : 09-04-2025
 - Developer  :  Janith Gamage
 - Change : Timecard Print - Employees

## Date : 30-07-2026
 - Change : Fix - Unapproved OT displaying on Time Card. `get_attendance_report()` was reading
   `normal_overtime`/`double_overtime`/`triple_overtime`/`holiday_hours` off every hr.attendance
   record regardless of `overtime_approval_status` (added by centrics_hr_overtime). Both the
   daily breakdown and the summed totals now only count these hours when
   `overtime_approval_status == 'approved'`; pending OT prints as blank/0:00. No other report
   logic (check-in/out, weekend/holiday/leave labeling) was changed.