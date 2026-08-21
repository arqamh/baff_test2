# Changelog

All notable changes to the Payroll Localization module will be documented in this file.

## [16.0.1.1.0] - 2025-12-30

### Added
- **EPF/ETF Calculation Control**:
  - New boolean field `add_to_calc_epf_etf` in hr.salary.rule
  - Allows configuring which salary rules should be included in EPF/ETF calculations
  - Default value set to False for backward compatibility

- **EPF/ETF Calculation Logic**:
  - New method `get_epf_etf_base()` in hr.payslip model
  - Automatically sums all salary rules marked with `add_to_calc_epf_etf = True`
  - Returns the base amount for EPF/ETF contribution calculations
  - Used by EPF/ETF salary rules in dependent modules (e.g., baff_hr_payroll_extend)
  - Enables flexible control over which salary components are included in EPF/ETF base

### Changed
- **Custom Settings Page Enhancement**:
  - Renamed "Report Settings" page to "Custom Settings" for better clarity
  - Added "Basic Settings" section with EPF/ETF calculation control
  - Reorganized page structure with distinct sections:
    - Basic Settings: EPF/ETF calculation options
    - Detail Payroll Report: Report visibility settings

### Technical
- Extended hr.salary.rule model:
  - Added `add_to_calc_epf_etf` Boolean field (default: False)
  - Allows marking individual salary rules for inclusion in EPF/ETF calculation
- Extended hr.payslip model:
  - Added `get_epf_etf_base()` method for calculating EPF/ETF base amount
  - Method iterates through payslip lines and sums amounts from rules marked for EPF/ETF
  - Returns total that can be used by EPF/ETF salary rules in any module
- Updated hr_salary_rule_views.xml:
  - Renamed page from "report_settings" to "custom_settings"
  - Added Basic Settings group with `add_to_calc_epf_etf` field
  - Maintained existing Detail Payroll Report group

### Documentation
- Updated README.md with:
  - New Custom Settings page documentation
  - Detailed explanation of Basic Settings and EPF/ETF calculation
  - New "EPF/ETF Calculation" section explaining:
    - How to mark salary rules for EPF/ETF inclusion
    - How the get_epf_etf_base() method works
    - Integration with dependent modules (e.g., baff_hr_payroll_extend)
    - Standard EPF/ETF rates
    - Example Python code for salary rule integration
  - Updated configuration instructions
- Enhanced feature descriptions for salary rule enhancements

---

## [16.0.1.0.0] - 2025-12-26

### Added
- Salary Rule enhancements:
  - Fixed Allowance/Deduction field for linking salary rules to fixed allowances
  - "Appear as Subtotal in Payslip" boolean field
  - Report Settings page in Salary Rule form view (positioned after Accounting tab)
- hr_payroll_account module dependency for accounting integration
- Extended salary rule form view with additional configuration options
- Integration with centrics_hr_attendance module

### Technical
- Extended hr.salary.rule model with new fields:
  - fixed_allowance_deduction_id (Many2one to fixed.allowance.deduction)
  - appear_as_subtotal_in_payslip (Boolean)
- Created hr_salary_rule_views.xml with form view inheritance
- Added Report Settings page using xpath after Accounting tab
- Added hr_payroll_account to module dependencies

### Views
- hr_salary_rule_form: Added Fixed Allowance/Deduction field after condition_select
- hr_salary_rule_form: Added "Appear as Subtotal in Payslip" after appears_on_payslip
- hr_salary_rule_form: Added Report Settings page (empty placeholder for extensions)

### Dependencies
- Requires hr_payroll_account module for full functionality
- Integrates with centrics_hr and centrics_hr_attendance
