# Employee Provident Fund (EPF)

## Overview
This module extends Odoo 16's HR functionality to manage Employee Provident Fund (EPF) information for both employees and companies. It provides comprehensive EPF tracking and ensures data integrity through validation rules.

## Features

### Company-Level EPF Settings
- **EPF-Employer Number**: Store company's EPF employer registration number
- **EPF-Zone Code**: Store EPF zone code for the company
- Dedicated EPF Settings tab in company configuration

### Employee-Level EPF Management
- **EPF Eligibility**: Mark employees as eligible/ineligible for EPF
- **EPF Number**: Store individual employee EPF numbers
- **Date of EPF Registration**: Track when employee was registered for EPF

### Salary Rule EPF/ETF Settings
- **Report Settings for Salary Rules**: Configure EPF/ETF reporting options for each salary rule
- **EPF 20%**: Mark salary rules that contribute to EPF at 20% rate
- **EPF 12%**: Mark salary rules that contribute to EPF at 12% rate (employer contribution)
- **EPF 8%**: Mark salary rules that contribute to EPF at 8% rate (employee contribution)
- **ETF 3%**: Mark salary rules that contribute to ETF at 3% rate

### EPF/ETF Reporting
- **EPF Contribution File Report**: Generate Excel reports for EPF contributions
- **Batch-based Reporting**: Generate reports for specific payroll batches
- **Automated Calculations**: Automatically calculates contributions based on salary rule settings
- **Excel Export**: Download formatted Excel file with all required statutory information
- **Standardized Format**: Generates reports with all columns required for EPF/ETF submissions

### Data Validation
- **Mandatory Name Fields for EPF**: When an employee is marked as EPF eligible:
  - Initials of the Name becomes mandatory
  - Last Name becomes mandatory
- Validation ensures data completeness for EPF-related reporting

## Configuration

### Company EPF Settings
1. Navigate to Settings > Companies > Your Company
2. Go to the "EPF Settings" tab
3. Enter:
   - EPF-Employer Number
   - EPF-Zone Code

### Employee EPF Settings
1. Navigate to Employees > Employees
2. Open an employee record
3. Enable "Eligible for EPF?" checkbox
4. When EPF eligible is checked:
   - Fill in required fields: Initials of the Name, Last Name
   - Enter EPF Number
   - Enter Date of EPF Registration

### Salary Rule EPF/ETF Configuration
1. Navigate to Payroll > Configuration > Salary Rules
2. Open a salary rule
3. Go to the "Report Settings" tab
4. In the EPF/ETF Settings section, check applicable options:
   - EPF 20%: For salary components that use total EPF rate
   - EPF 12%: For employer's EPF contribution
   - EPF 8%: For employee's EPF contribution
   - ETF 3%: For employer's ETF contribution
5. These settings help generate accurate EPF/ETF reports

## Generating EPF/ETF Reports

### EPF Contribution File
1. Navigate to Payroll > Reporting > EPF/ETF Reports > EPF Contribution File
2. A wizard will popup
3. Select the Payroll Batch from the dropdown
4. Click "Generate Excel" button
5. Excel file will be automatically downloaded

### Excel Report Columns
The generated Excel file includes the following columns:
1. **NIC/Passport Number**: Employee's identification number
2. **Last Name**: Employee's last name
3. **Initials**: Employee's name initials
4. **Member AC Number**: Employee's EPF number
5. **Total Contribution**: Combined employer and employee EPF contributions
6. **Employer's Contribution**: Calculated from salary rules marked as EPF 12%
7. **Member's Contribution**: Calculated from salary rules marked as EPF 8%
8. **Total Earnings**: Total from salary rules marked as EPF 20%
9. **Member Status**: E=Existing, N=New, V=Vacated
10. **Zone Code**: Company's EPF zone code
11. **Employer Number**: Company's EPF employer number
12. **Contribution Year & Month**: Period from payslip
13. **Data Submission Number**: Submission sequence number
14. **No of Days Worked**: Total worked days from payslip
15. **Occupation Classification Grade**: Employee's job position

### File Naming Convention
Downloaded files are named as: `<batch_name>_epf_contribution_<current_date>.xlsx`

Example: `January_2025_epf_contribution_20251226.xlsx`

## Validation Rules

### EPF Eligible Employees
When an employee is marked as EPF eligible, the system enforces:
1. **Initials of the Name**: Must be filled
2. **Last Name**: Must be filled

If either field is missing, the system will display an error message:
- "Initials of the Name is required when employee is eligible for EPF."
- "Last Name is required when employee is eligible for EPF."

## Dependencies

### Odoo Modules
- base
- hr
- centrics_hr
- hr_payroll
- centrics_hr_payroll

### Python Libraries
- xlsxwriter (for Excel report generation)

## Author
Centrics Business Solutions (Pvt) Ltd
Website: https://www.centrics.lk

## License
OPL-1

## Version
16.0.1.0.0

## Notes

### General
- EPF fields on employee form are visible only when "Eligible for EPF?" is checked
- EPF Number and Date of EPF Registration are required when employee is EPF eligible
- Company EPF settings are optional but recommended for complete EPF management
- Salary Rule Report Settings page requires centrics_hr_payroll module to be installed
- EPF/ETF checkboxes on salary rules help identify which rules contribute to statutory funds
- Multiple EPF/ETF options can be checked on a single salary rule if applicable

### EPF Report Requirements
- **xlsxwriter library**: Required for Excel generation. Install with: `pip install xlsxwriter`
- **Salary Rules Configuration**: Ensure salary rules are properly marked with EPF/ETF percentages
- **Company EPF Data**: Set up EPF Employer Number and Zone Code for accurate reports
- **Employee Data**: Ensure employees have NIC/Passport, Last Name, Initials, and EPF Number
- **Payslip Status**: Only payslips in 'Done' state are included in the report
- The report automatically filters EPF-eligible employees from the selected batch
