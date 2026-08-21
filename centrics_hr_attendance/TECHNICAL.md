==============================
Technical Documentation
==============================

Module Name: centrics_hr_attendance  
Version: 16.0.1.0.1  
Category: Localization

Overview
========

This module enhances the HR Attendance system by introducing configurable and automatable attendance logging using manual entry forms and background jobs.

Models Introduced
=================

1. `hr.attendance.import.configuration`
   - Stores configuration settings for importing or entering attendance manually.
   - Used to define allowed users, date ranges, and constraints.

2. `hr.attendance.manual.log`
   - Stores individual manual attendance log entries.
   - Supports employee, check-in, and check-out fields.

3. `attendance.manual.uploader`
   - A wizard model to bulk upload manual attendance entries (e.g., from CSV/Excel).
   - Allows user-friendly data entry and import validation.

4. Modified: `hr.attendance`
   - Extended to integrate with manually created attendance records.
   - Ensures consistency between logs and official entries.

Security & Access Control
=========================

- Custom security groups defined in:
  - `centrics_hr_attendance_groups.xml`
  - `centrics_hr_attendance_security.xml`

- Access rights managed via:
  - `ir.model.access.csv`

Automated Actions
=================

- Cron Job: `ir_cron_data.xml`
  - Scheduled action to convert valid manual logs into system attendance records.
  - Runs at a configured interval (daily/hourly) based on cron settings.

Views & Menus
=============

- Menu: `centrics_hr_attendance_menus.xml`
- Views:
  - Attendance configuration
  - Manual attendance logs
  - Manual uploader wizard
  - Attendance records view extension

Notes
=====

- Ensure proper employee setup for attendance processing.
- Users must have the correct access rights to manage logs or configurations.
