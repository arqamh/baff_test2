# Changelog

All notable changes to the HR Overtime module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [16.0.1.1.0] - 2026-02-06

### Added

#### Deduction Source Configuration
- **New Field**: `deduction_source` on `hr.overtime.template`
  - Selection field with two options:
    - **Deduct from Worked Hours** (`worked_hours`): Deductions are collected from all applicable rules and subtracted from total worked hours **before** overtime rules are evaluated. OT rules then operate on the reduced hours without per-rule deductions.
    - **Deduct From OT Hours** (`ot_hours`, default): Deductions are applied per-rule during overtime allocation (existing behavior).
  - Rendered as radio buttons in the template form view under "Dynamic Deduction Configurations"
  - Respects template lock state (read-only when locked)
  - Tracked field for audit trail

- **New Method**: `_collect_applicable_deductions()` on `hr.attendance`
  - Collects all unique applicable deductions across all rules for a given attendance record
  - Deduplicates deductions shared across multiple rules
  - Returns total deduction in hours after validating each deduction's time window

#### Enhanced Views
- **Overtime Template Form**: Added "Dynamic Deduction Configurations" group with radio widget above "System Configurations"

### Changed
- **`_apply_rules_for_duration()`**: Added `template` parameter
  - When `deduction_source == 'worked_hours'`: deductions are subtracted from `duration_hours` upfront, and `skip_deductions=True` is passed to `compute_overtime_allocation()`
  - When `deduction_source == 'ot_hours'`: existing per-rule deduction behavior is preserved
- **`compute_overtime_allocation()`**: Added `skip_deductions` parameter
  - When `True`, per-rule deduction calculation is skipped entirely (already applied upfront)
- **`_compute_overtime()`**: All calls to `_apply_rules_for_duration()` now pass the `template` argument

### Technical Details

#### Files Modified
- `models/hr_overtime_template.py` - Added `deduction_source` selection field
- `models/hr_attendance.py` - Added `_collect_applicable_deductions()`, updated `_apply_rules_for_duration()` and `compute_overtime_allocation()` signatures, updated all call sites in `_compute_overtime()`
- `views/hr_overtime_template_views.xml` - Added Dynamic Deduction Configurations group with radio widget
- `README.md` - Updated documentation for deduction source configuration
- `CHANGELOG.md` - Added version 16.0.1.1.0 entry

#### Database Schema Changes
- New column `deduction_source` on `hr_overtime_template` table (Selection, required, default `'ot_hours'`)

---

## [16.0.1.0.0] - 2025-12-29

### Added

#### Dynamic Deductions Feature
- **New Model**: `overtime.dynamic.deduction`
  - Allows users to define custom deduction names
  - Configure deduction time in minutes
  - Full CRUD access for base.group_user
  - **Deletion Protection**: Prevents deletion of deductions in use
    - Checks if deduction is referenced in any overtime rule
    - Displays helpful error message with template names
    - Ensures referential integrity

- **Settings Menu Structure**
  - Added "Settings" menu under Attendances App > Overtime
  - Added "Dynamic Deductions" submenu under Settings
  - Tree view with editable bottom for quick entry

- **Integration with Overtime Rules**
  - Added `deduction_ids` Many2many field to `hr.overtime.rule` model
  - Enables multiple deduction selection per overtime rule
  - Deductions displayed as tags in all views for better visibility

#### Enhanced Views
- **Overtime Rule Views**
  - Added deduction_ids field with many2many_tags widget in form view
  - Added deduction_ids field with many2many_tags widget in tree view

- **Overtime Template Views**
  - Added deduction_ids field to rule_ids tree view (Overtime Rules tab)
  - Added deduction_ids field to multiple_rule_ids tree view (Overtime Rules for Extra Days tab)
  - Inline editing support for deductions in both tabs
  - **Template Lock Enhancement**: Implemented comprehensive read-only mode for locked templates
    - All fields become read-only when template state is 'lock'
    - Lock button hidden when template is locked
    - Set to Draft button hidden when template is in draft
    - Overtime rules (One2many fields) become non-editable when locked
    - Ensures data integrity for production templates

### Changed
- **Overtime Calculation Logic**: Enhanced to automatically apply dynamic deductions
  - Deductions are calculated and applied during overtime allocation
  - Deduction time (in minutes) is converted to hours and subtracted from allocated overtime
  - Applied to all rule conditions: full_day, upto_hours, and remaining_hours
  - Ensures overtime never goes negative after deduction
- Updated access rights CSV to include overtime.dynamic.deduction model
- Enhanced overtime rule configuration with deduction capabilities
- Improved user experience with tag-based deduction display
- **Template Lock Behavior**: Enhanced locking mechanism for better data protection
  - All template fields become read-only when locked
  - Dynamic button visibility based on template state
  - Prevents accidental modifications to finalized templates
  - Maintains template usability while preventing edits

### Technical Details

#### Files Added
- `models/overtime_dynamic_deduction.py` - Dynamic deduction model
- `views/overtime_dynamic_deduction_views.xml` - Views and menus for dynamic deductions
- `README.md` - Comprehensive module documentation
- `CHANGELOG.md` - Version history and changes

#### Files Modified
- `models/__init__.py` - Added overtime_dynamic_deduction import
- `models/overtime_dynamic_deduction.py` - Added unlink() method override for deletion protection
- `models/hr_overtime_rule.py` - Added deduction_ids Many2many field
- `models/hr_attendance.py` - Enhanced compute_overtime_allocation() to apply deductions
- `views/hr_overtime_rule_views.xml` - Added deduction_ids to form and tree views
- `views/hr_overtime_template_views.xml` - Enhanced with:
  - Added deduction_ids to both rule tree views
  - Implemented read-only attributes for all fields when state='lock'
  - Added button visibility controls based on template state
- `security/ir.model.access.csv` - Added access rights for overtime.dynamic.deduction
- `__manifest__.py` - Added overtime_dynamic_deduction_views.xml to data files

### Database Schema Changes
- New table: `overtime_dynamic_deduction`
  - `id`: Integer (Primary Key)
  - `name`: Char (Required) - Deduction Name
  - `deduction_time`: Integer (Required) - Deduction Time in Minutes
  - Standard Odoo audit fields (create_date, create_uid, write_date, write_uid)

- New relation table: `hr_overtime_rule_overtime_dynamic_deduction_rel`
  - Links hr.overtime.rule with overtime.dynamic.deduction (Many2many)

### Security
- Full access (read, write, create, unlink) granted to `base.group_user` for dynamic deductions
- Follows existing module security patterns
- **Data Integrity Protection**:
  - Deletion constraint prevents removal of deductions in use
  - Referential integrity maintained between deductions and rules
  - User-friendly error messages guide proper data management

---

## [16.0.0.1.0] - Previous Release

### Initial Features

#### Core Functionality
- Overtime template management with job position assignment
- Global and position-specific templates
- Template locking mechanism for data integrity
- Active/Inactive template management

#### Overtime Rules
- Three overtime types: Normal, Double, Triple
- Multiple application scopes:
  - Scheduled Days (Check In/Check Out)
  - Weekends
  - Public/Mercantile Holidays
  - All Days
- Flexible conditions:
  - Upto X Hours
  - Remaining Hours
  - Full Day
- Threshold-based calculations

#### Working Day Configuration
- Pre-defined check-in/check-out times
- Working schedule integration
- Custom time configurations per template

#### Multi-Day Overtime
- Enable overtime across multiple days
- Continue from first day option
- Separate rules for extra days

#### Pre-Approval System
- Overtime pre-approval workflow
- User and Manager role separation
- Request tracking and history

#### Buffer Time Configuration
- Employee type-based buffer time settings
- Optional buffer time bypass
- Validation for buffer time values
- Unique constraint per employee type

#### Integration
- Seamless HR Attendance integration
- Employee contract support
- Company-specific configurations

#### Security Groups
- Overtime - User
- Overtime - Manager
- Overtime Pre Approval - User
- Overtime Pre Approval - Manager

#### Reporting
- Employee overtime reports
- Attendance-based overtime tracking

#### User Interface
- Intuitive menu structure under Attendances App
- Form and tree views for all models
- Chatter integration for templates
- Activity tracking
- Drag-and-drop rule sequencing

---

## Upgrade Instructions

### From 16.0.0.1.0 to 16.0.1.0.0

1. **Backup your database** before upgrading

2. **Update the module files** in your addons directory

3. **Restart Odoo server**
   ```bash
   sudo systemctl restart odoo
   ```

4. **Upgrade the module**
   - Go to Apps menu
   - Remove the "Apps" filter
   - Search for "HR Overtime"
   - Click "Upgrade"

5. **Verify the upgrade**
   - Check that "Settings" menu appears under Attendances > Overtime
   - Verify "Dynamic Deductions" submenu is accessible
   - Test creating a new dynamic deduction
   - Confirm deduction_ids field appears in overtime rules

6. **Clear browser cache** to ensure all view changes are loaded

### Database Migration Notes
- New table `overtime_dynamic_deduction` will be created automatically
- New Many2many relation table will be created automatically
- Existing overtime rules will have empty deduction_ids (no data loss)
- All existing data remains intact

---

## Future Enhancements (Planned)

- [ ] Deduction templates for common deduction scenarios
- [ ] Deduction calculation based on percentage
- [ ] Advanced reporting with deduction breakdowns
- [ ] Bulk deduction assignment to multiple rules
- [ ] Deduction history and audit trail
- [ ] Import/Export functionality for deductions

---

**Note**: This changelog is maintained by Centrics Business Solutions (Pvt) Ltd. For detailed technical changes, please refer to the git commit history.
