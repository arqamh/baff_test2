# HR Overtime Management

**Version:** 16.0.1.0.0
**Author:** Centrics Business Solutions (Pvt) Ltd
**Website:** http://www.centrics.cloud/
**License:** OPL-1

## Overview

The HR Overtime module is a comprehensive solution for managing employee overtime in Odoo 16. It provides flexible overtime calculation rules, pre-approval workflows, and seamless integration with the HR Attendance module.

## Key Features

### 1. Overtime Templates
- Create multiple overtime templates for different job positions or as global templates
- Configure working day parameters:
  - Pre-defined check-in and check-out times
  - Integration with employee working schedules
- Support for multiple days overtime calculations
- **Template locking mechanism** to prevent accidental changes:
  - Lock templates to make all fields read-only
  - Locked templates cannot be modified until unlocked
  - Prevents unauthorized changes to finalized configurations
  - Only "Set to Draft" action available when locked
- Active/Inactive status management

### 2. Overtime Rules
Flexible overtime calculation with three rule types:
- **Normal OT**: Standard overtime rates
- **Double OT**: Double-time overtime rates
- **Triple OT**: Triple-time overtime rates

#### Rule Conditions
- **Upto X Hours**: Calculate overtime up to a specified threshold
- **Remaining Hours**: Calculate overtime for remaining hours after threshold
- **Full Day**: Apply overtime for full day work

#### Application Scope
- Scheduled Days (Check In)
- Scheduled Days (Check Out)
- Weekends
- Public/Mercantile Holidays
- All Days

### 3. Dynamic Deductions
- Define custom deduction rules with time values in minutes
- Apply multiple deductions to overtime rules
- Flexible deduction management through an easy-to-use interface
- Displayed as tags for better visibility
- **Configurable deduction source** per template:
  - **Deduct from Worked Hours**: Deductions are subtracted from total worked hours before overtime rules are evaluated. This reduces the base hours used for OT calculation.
  - **Deduct From OT Hours** (default): Deductions are subtracted from overtime hours after rules allocate them into OT buckets (per-rule deduction).
- **Protected deletion**: Deductions in use cannot be deleted
  - System prevents deletion if deduction is assigned to any overtime rule
  - Shows which templates are using the deduction
  - Ensures data integrity and prevents broken references

### 4. Overtime Pre-Approval
- Request overtime approval before actual work
- Approval workflow with user and manager roles
- Track approval status and history

### 5. Buffer Time Configuration
- Configure buffer times based on employee types
- Option to avoid buffer time for specific employee categories
- Validation to ensure buffer time is properly configured

### 6. Multi-Day Overtime Support
- Enable overtime calculations spanning multiple days
- Option to continue from the first day
- Use separate overtime rules for extra days

### 7. Integration with HR Attendance
- Automatic overtime calculation based on attendance records
- Support for different working schedules
- Integration with employee contracts

## Installation

1. Copy the module to your Odoo addons directory:
   ```
   /path/to/odoo/addons/centrics_hr_overtime
   ```

2. Update the apps list:
   - Go to Apps menu
   - Click "Update Apps List"

3. Install the module:
   - Search for "HR Overtime"
   - Click Install

## Configuration

### Initial Setup

1. **Navigate to Attendances App**
   - Go to Attendances App in the main menu

2. **Create Overtime Templates**
   - Navigate to: Attendances > Overtime > Overtime Templates
   - Click "Create"
   - Configure:
     - Template name
     - Job positions (leave empty for global template)
     - Working day settings
     - Enable multi-day options if needed

3. **Define Overtime Rules**
   - Within the template, add overtime rules in the "Overtime Rules" tab
   - Configure:
     - Rule type (Normal/Double/Triple)
     - Application scope (Scheduled Days/Weekends/Holidays/All)
     - Conditions (Upto X Hours/Remaining Hours/Full Day)
     - Threshold hours (if applicable)
     - Dynamic deductions (optional)

4. **Configure Dynamic Deductions** (Optional)
   - Navigate to: Attendances > Overtime > Settings > Dynamic Deductions
   - Create deduction rules with:
     - Deduction name
     - Deduction time in minutes
   - Assign deductions to overtime rules as needed
   - In the Overtime Template, configure the **Deduction Source**:
     - **Deduct from Worked Hours**: Deductions reduce worked hours before OT rules run
     - **Deduct From OT Hours**: Deductions reduce OT hours per rule (default)

5. **Set Up Buffer Time** (Optional)
   - Configure buffer times for different employee types
   - Define whether to avoid buffer time for specific categories

### User Access Rights

The module provides four security groups:

1. **Overtime - User**: Basic overtime access
2. **Overtime - Manager**: Overtime approval and management
3. **Overtime Pre Approval - User**: Can create pre-approval requests
4. **Overtime Pre Approval - Manager**: Can approve/reject requests

Assign users to appropriate groups via Settings > Users & Companies > Users.

## Usage

### Creating Overtime Templates

1. Go to **Attendances > Overtime > Overtime Templates**
2. Click **Create**
3. Fill in the template details:
   - Name: Give a descriptive name
   - Job Positions: Select specific positions or leave empty for global
   - For Working Days: Choose between predefined times or working schedules
   - Check-in/Check-out times (if using predefined)
4. Add overtime rules in the "Overtime Rules" tab
5. Click **Lock** when the template is finalized

### Adding Dynamic Deductions to Rules

1. Open an Overtime Template
2. In the "Overtime Rules" tab, add or edit a rule
3. In the **Deductions** field, select one or more dynamic deductions
4. The deductions will appear as tags
5. Save the template

### Configuring Deduction Source

Each overtime template has a **Dynamic Deduction Configurations** section with two options:

- **Deduct from Worked Hours**: All applicable deductions are collected and subtracted from the total worked/OT hours **before** overtime rules are evaluated. The OT rules then operate on the reduced hours without applying any further deductions.
- **Deduct From OT Hours** (default): Deductions are applied **per rule** during overtime allocation. Each rule subtracts its assigned deductions from its own allocated hours.

**Example** (30-minute lunch deduction, 10 total worked hours, rule: Normal OT - Full Day):
- *Deduct from Worked Hours*: 10h - 0.5h = 9.5h worked -> rule allocates 9.5h Normal OT
- *Deduct From OT Hours*: rule allocates 10h -> 10h - 0.5h = 9.5h Normal OT

### Locking and Unlocking Templates

#### Locking a Template
When an overtime template is finalized and ready for production use:

1. Open the Overtime Template
2. Click the **Lock** button in the header
3. The template state changes to "Lock"
4. All fields become read-only (greyed out):
   - Template name and configurations
   - Job positions
   - Working day settings
   - Multi-day options
   - Overtime rules (cannot add, edit, or delete)
   - System configurations
5. The Lock button disappears
6. Only the **Set to Draft** button remains visible

**Benefits of Locking:**
- Prevents accidental modifications to production templates
- Ensures data integrity for active overtime calculations
- Provides audit trail of when template was finalized
- Forces deliberate action to make changes

#### Unlocking a Template
To modify a locked template:

1. Open the locked Overtime Template
2. Click the **Set to Draft** button in the header
3. The template state changes to "Draft"
4. All fields become editable again
5. The Set to Draft button disappears
6. The **Lock** button reappears
7. Make necessary changes
8. Click **Lock** again when finished

**Important Notes:**
- Only users with appropriate permissions can lock/unlock templates
- Locked templates can still be used for overtime calculations
- Locking does not affect active/inactive status
- Always lock templates after configuration is complete

### Managing Employee Overtime

1. Employee attendance is tracked through the HR Attendance module
2. Overtime is automatically calculated based on:
   - Assigned overtime template (via job position)
   - Configured overtime rules
   - Actual check-in/check-out times
   - Applied deductions

### Pre-Approval Workflow

1. Employee or manager creates a pre-approval request
2. Manager reviews and approves/rejects the request
3. Approved overtime is tracked against actual attendance

## Menu Structure

```
Attendances App
└── Overtime
    ├── Overtime Templates
    ├── Overtime Rules
    ├── Overtime Pre-Approvals
    ├── Buffer Time Configuration
    └── Settings
        └── Dynamic Deductions
```

## Technical Information

### Dependencies
- `base`
- `hr`
- `hr_attendance`

### Models

| Model | Description |
|-------|-------------|
| `hr.overtime.template` | Overtime template configuration |
| `hr.overtime.rule` | Individual overtime calculation rules |
| `overtime.dynamic.deduction` | Time deduction configurations |
| `hr.overtime.pre.approval` | Overtime pre-approval requests |
| `buffer.time.configuration` | Buffer time settings by employee type |
| `make.employee.overtime` | Wizard for generating employee overtime |

### Key Fields

#### hr.overtime.template
- `deduction_source`: Selection field (`worked_hours` / `ot_hours`) - Controls whether dynamic deductions are subtracted from worked hours before OT rules or from OT hours per rule

#### hr.overtime.rule
- `name`: Rule name (auto-generated)
- `rule_type`: Normal/Double/Triple OT
- `apply_on`: Application scope
- `condition`: Calculation condition
- `threshold_hours`: Hours threshold for conditions
- `deduction_ids`: Related dynamic deductions (Many2many)
- `sequence`: Display order

#### overtime.dynamic.deduction
- `name`: Deduction name
- `deduction_time`: Time in minutes to deduct

## Troubleshooting

### Common Issues

**Issue**: Overtime not calculating correctly
- **Solution**: Check that the overtime template is assigned to the employee's job position
- Verify that the overtime rules are configured with correct thresholds
- Ensure the template is in "Lock" state

**Issue**: Cannot see Dynamic Deductions menu
- **Solution**: Ensure you have appropriate access rights (base.group_user or higher)
- Verify the module is properly upgraded after installation

**Issue**: Deductions not applying
- **Solution**: Check that deductions are assigned to the overtime rule
- Verify the deduction time values are set correctly
- Check the **Deduction Source** setting on the overtime template:
  - "Deduct from Worked Hours" applies deductions before OT rules
  - "Deduct From OT Hours" applies deductions per rule during allocation

**Issue**: Cannot edit overtime template fields
- **Solution**: Check if the template is in "Lock" state
- Click "Set to Draft" button to unlock the template
- Make your changes, then lock it again when finished

**Issue**: Lock/Set to Draft button not visible
- **Solution**: The "Lock" button only appears when template is in Draft state
- The "Set to Draft" button only appears when template is in Lock state
- Ensure you have appropriate permissions to lock/unlock templates

**Issue**: Cannot delete a dynamic deduction
- **Solution**: The deduction is being used in one or more overtime rules
- Check the error message to see which templates are using it
- Remove the deduction from all overtime rules first
- Then you can delete the deduction record

## Support

For support and inquiries:
- **Website**: http://www.centrics.cloud/
- **Author**: Centrics Business Solutions (Pvt) Ltd

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.

## License

This module is licensed under OPL-1 (Odoo Proprietary License v1.0).

---

**Centrics Business Solutions (Pvt) Ltd** - Building Better Business Solutions
