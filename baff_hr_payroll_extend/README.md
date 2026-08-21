# baff_hr_payroll_extend — Ocean Voyager Payroll Extensions

Client-specific payroll module for Ocean Voyager. Adds two salary structures (Staff and Non-Staff), OT calculation, allowances, deductions, EPF, APIT, and a monthly salary sheet Excel report.

## Features

### Salary Structures

- **Staff** — 24-line structure with Normal OT, Holiday OT, Special Incentive, Attendance Allowance, Special Allowance, EPF 8%, APIT, Nopay (÷30), Net Salary.
- **Non-Staff** — 28-line structure adding Double OT, Triple OT, Leader Allowance, Relocation Payment, Nopay (÷26).

### OT Rate Computation

Three computed fields on `hr.contract` derive per-hour OT rates from the contract wage and the employee's Ocean Voyager category:

- Staff: monthly divisor **240 hours**
- Non-Staff: monthly divisor **200 hours**

Rates: Normal (×1.5), Double (×2.0), Triple (×3.0). Rates are stored and update automatically when wage or category changes. A manual refresh button is available on the contract form.

### Payslip Input Auto-Population

When a payslip is computed, the module automatically populates inputs from:
- Attendance records (Normal / Double / Triple OT hours, Holiday hours, attendance count)
- Leave records (No-pay days — overlap-aware, using Date fields to avoid Datetime comparison bugs)
- Employee loan installments
- Contract fixed allowances and deductions

### Salary Sheet Excel Report

Available at **Payroll → Reporting → Custom Reports → Salary Sheet**.

Select a payroll batch and employee category (Staff or Non-Staff) to download an `.xlsx` file with:
- Company name and report title header rows
- Orange numbered + labelled column headers
- One row per employee (sorted by name)
- Totals row

Staff sheet: 24 columns. Non-Staff sheet: 28 columns. See `TECHNICAL.md` for the full column mapping.

## Dependencies

Requires: `hr_payroll`, `baff_hr_extend`, `baff_hr_overtime_extend`, `centrics_hr_allowance_deduction`, `centrics_hr_loan_management`, `centrics_hr_payroll`.

Requires `xlsxwriter` Python library for Excel generation (`pip install xlsxwriter`).

## Documentation

- `TECHNICAL.md` — full model reference, salary rule tables, wizard column layouts.
- `CHANGELOG.md` — version history.
