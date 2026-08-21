# Changelog

All notable changes to the Employee Provident Fund module will be documented in this file.

## [16.0.1.0.0] - 2025-12-26

### Added
- Company-level EPF configuration fields:
  - EPF-Employer Number field
  - EPF-Zone Code field
  - EPF Settings tab in company form view
- Employee-level EPF management fields:
  - Eligible for EPF checkbox
  - EPF Number field (visible when eligible)
  - Date of EPF Registration field (visible when eligible)
- Data validation for EPF eligible employees:
  - Initials of the Name is mandatory when EPF eligible
  - Last Name is mandatory when EPF eligible
  - Validation constraint with clear error messages
- Salary Rule EPF/ETF configuration fields:
  - EPF 20% checkbox for total EPF rate
  - EPF 12% checkbox for employer's EPF contribution
  - EPF 8% checkbox for employee's EPF contribution
  - ETF 3% checkbox for employer's ETF contribution
- EPF/ETF Reporting system:
  - EPF Contribution File wizard for batch-based report generation
  - Excel export functionality with xlsxwriter
  - Automated calculation of EPF/ETF contributions from payslip lines
  - 15 standardized report columns for statutory compliance
  - Dynamic file naming: `<batch_name>_epf_contribution_<date>.xlsx`
- Menu structure:
  - EPF/ETF Reports menu under Payroll > Reporting
  - EPF Contribution File menu item with wizard action
- View enhancements:
  - EPF fields visibility controlled by eligibility checkbox
  - Required field indicators in UI for EPF eligible employees
  - Conditional required attributes on name fields
  - EPF/ETF Settings group in Salary Rule Report Settings page
  - Wizard popup for EPF report generation

### Technical
- Extended res.company model with EPF-related fields
- Extended hr.employee model with EPF eligibility and registration fields
- Extended hr.salary.rule model with EPF/ETF reporting fields:
  - epf_20 (Boolean)
  - epf_12 (Boolean)
  - epf_8 (Boolean)
  - etf_3 (Boolean)
- Created epf.contribution.report.wizard transient model:
  - payslip_batch_id (Many2one to hr.payslip.run)
  - action_generate_excel() method for Excel generation
  - Automatic calculation logic based on salary rule EPF/ETF flags
  - Excel formatting with headers and data sections
- Implemented @api.constrains validation for EPF required fields
- Created res_company_views.xml with EPF Settings page
- Created hr_employee_views.xml with EPF field integration
- Created hr_salary_rule_views.xml with EPF/ETF fields in Report Settings page
- Created epf_contribution_report_wizard_views.xml with wizard form and menu
- Added conditional required attributes using Odoo attrs
- Added centrics_hr_payroll module dependency
- Created security/ir.model.access.csv for wizard access rights

### Validation Rules
- `_check_epf_required_fields`: Validates that name_initials and last_name are filled when employee is EPF eligible
- Raises ValidationError with user-friendly messages when validation fails

### Dependencies
- Depends on centrics_hr module for name fields (name_initials, first_name, middle_name, last_name)
- Depends on centrics_hr_payroll module for Report Settings page in Salary Rules
- Integrates with standard Odoo hr and hr_payroll modules
- Requires xlsxwriter Python library for Excel report generation

### Files
- models/hr_employee.py: Employee EPF fields and validation
- models/res_company.py: Company EPF configuration fields
- models/hr_salary_rule.py: Salary Rule EPF/ETF reporting fields
- wizard/epf_contribution_report_wizard.py: EPF report wizard model with Excel generation
- views/hr_employee_views.xml: Employee EPF form view extensions
- views/res_company_views.xml: Company EPF Settings page
- views/hr_salary_rule_views.xml: Salary Rule Report Settings with EPF/ETF fields
- wizard/epf_contribution_report_wizard_views.xml: Wizard form, action, and menu structure
- security/ir.model.access.csv: Access rights for wizard model

### Report Columns
The EPF Contribution File report includes 15 columns:
1. NIC/Passport Number
2. Last Name
3. Initials
4. Member AC Number (EPF Number)
5. Total Contribution
6. Employer's Contribution
7. Member's Contribution
8. Total Earnings
9. Member Status (E/N/V)
10. Zone Code
11. Employer Number
12. Contribution Year & Month
13. Data Submission Number
14. No of Days Worked
15. Occupation Classification Grade
