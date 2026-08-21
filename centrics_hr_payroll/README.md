# Payroll Localization

## Overview
This module provides localized payroll functionality for Odoo 16, extending the standard HR Payroll features with additional fields and reporting capabilities specific to regional requirements.

## Features

### Salary Rule Enhancements
- **Fixed Allowance/Deduction**: Link salary rules to fixed allowances or deductions for consistent payroll processing
- **Subtotal Display**: Option to display salary rules as subtotals in payslip reports
- **Custom Settings Page**: Dedicated page for configuring salary rule custom options
  - **Basic Settings**: Configure EPF/ETF calculation inclusion
  - **Report Settings**: Control appearance in detail payroll reports

### Employee Payroll Fields
- Extended employee records with additional payroll-related fields
- Integration with attendance tracking for payroll calculations

### Custom Settings
The Custom Settings page in the Salary Rule form provides a dedicated space for configuring salary rule behavior and reporting options. This page is positioned after the Accounting tab for easy access to all configuration options.

#### Basic Settings
- **Add to Cal EPF/ETF**: Enable this option to include the salary rule amount in EPF/ETF contribution calculations
  - When enabled, the rule amount will be added to the base salary for EPF/ETF computation
  - Essential for allowances that should be included in statutory contributions

#### Detail Payroll Report
- **Appear on Detail Payroll Report**: Control whether this salary rule appears in detailed payroll reports
  - When enabled, the rule will be visible in comprehensive payroll breakdowns
  - Useful for transparency and audit purposes

## EPF/ETF Calculation

The module provides the calculation logic for EPF (Employees' Provident Fund) and ETF (Employees' Trust Fund) contributions based on salary rules marked for inclusion.

### How It Works

1. **Mark Salary Rules**: Use the "Add to Cal EPF/ETF" checkbox in the Custom Settings tab to mark which salary rules should be included in EPF/ETF calculations (e.g., Basic Salary, Allowances)
2. **Base Calculation**: The `get_epf_etf_base()` method automatically sums all payslip line amounts where the salary rule has "Add to Cal EPF/ETF" enabled
3. **Automatic Computation**: EPF and ETF salary rules (defined in dependent modules like `baff_hr_payroll_extend`) call this method to calculate contributions
4. **Standard Rates**:
   - **EPF Employee (8%)**: Deducted from employee's salary
   - **EPF Employer (12%)**: Company contribution
   - **ETF Employer (3%)**: Company contribution

### Integration with Salary Structures

The `get_epf_etf_base()` method is used by EPF/ETF salary rules defined in dependent modules. For example, in `baff_hr_payroll_extend`, the salary rules use:

```python
# EPF 8% (Employee Deduction)
result = -1 * payslip.get_epf_etf_base() * 0.08

# EPF 12% (Employer Contribution)
result = payslip.get_epf_etf_base() * 0.12

# ETF 3% (Employer Contribution)
result = payslip.get_epf_etf_base() * 0.03
```

This approach allows flexible EPF/ETF calculation where you control which salary components are included in the base amount.

## Configuration

### Salary Rules
1. Navigate to Payroll > Configuration > Salary Rules
2. Open or create a salary rule
3. In the General tab:
   - Select a Fixed Allowance/Deduction if applicable
   - Check "Appear as Subtotal in Payslip" to display the rule as a subtotal
4. Use the Custom Settings tab to configure:
   - **Basic Settings**:
     - Check "Add to Cal EPF/ETF" to include this rule in EPF/ETF calculations
   - **Detail Payroll Report**:
     - Check "Appear on Detail Payroll Report" to show this rule in detailed reports

## Dependencies
- base
- hr
- hr_payroll
- hr_payroll_account
- centrics_hr
- centrics_hr_attendance

## Author
Centrics Business Solutions (Pvt) Ltd
Website: https://www.centrics.lk

## License
OPL-1

## Version
16.0.1.1.0
