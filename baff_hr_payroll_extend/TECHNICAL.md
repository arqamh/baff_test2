# Technical Reference — baff_hr_payroll_extend

## Module Overview

| Field | Value |
|---|---|
| Technical name | `baff_hr_payroll_extend` |
| Display name | Ocean Voyager Payroll Extensions |
| Version | 18.0.1.0.9 |
| Odoo base | 16 (version string uses 18.0 convention) |
| License | OPL-1 |

### Dependencies

```
hr, hr_contract, hr_payroll,
baff_hr_extend,                    # ocean_voyager_emp_category field
baff_hr_overtime_extend,           # hr.attendance OT fields
centrics_hr_allowance_deduction,   # fixed.allowance.deduction model
centrics_hr_loan_management,       # employee.loan.type / employee.loan.installment.line
centrics_hr_payroll,               # base payslip compute override
centrics_hr_payroll_no_default_rules  # suppress generic default salary rules on new structures
```

---

## Models

### Default salary rule prevention

The suppression of Odoo's eight generic salary rules on new
`hr.payroll.structure` records is provided by the reusable foundation module
**`centrics_hr_payroll_no_default_rules`** (added to `depends`), which overrides
`default_get`. See that module's `TECHNICAL.md` for the rationale and
implementation.

This module ships the project-specific data cleanup that removes generic rules
already injected into the three BAFF structures by earlier installs — see
`migrations/18.0.1.0.8/post-migration.py`.

---

### `hr.payslip` — `models/hr_payslip.py`

Inherits `hr.payslip`. Overrides `_compute_input_line_ids` to auto-populate payslip inputs from attendance, leave, and contract data.

#### Helper methods

| Method | Returns | Description |
|---|---|---|
| `_get_attendance_records(employee_id, date_from, date_to)` | dict | `ATTND_ALLW` input — count of attendance records in range |
| `_get_normal_ot_hours(employee_id, date_from, date_to)` | dict | `NORM_OT_HRS` — sum of `normal_overtime` from approved OT attendance |
| `_get_double_ot_hours(employee_id, date_from, date_to)` | dict | `DBL_OT_HRS` — sum of `double_overtime` |
| `_get_triple_ot_hours(employee_id, date_from, date_to)` | dict | `TRPL_OT_HRS` — sum of `triple_overtime` |
| `_get_holiday_count(employee_id, date_from, date_to)` | dict | `HOL_HRS` — sum of `holiday_hours` from approved OT attendance |
| `_get_no_pay_count(employee_id, date_from, date_to)` | dict | `NOPAY` — total no-pay days from validated `hr.leave` records |
| `_get_no_of_experience(employee_id, date_to)` | dict | `NO_EXP` — years since `employee.joined_date` |
| `_get_relocation_allowance()` | dict | `REl_ALW` — placeholder, always 0 |
| `_get_leave_balance()` | dict | `LEAVE_ALLW` — placeholder, always 0 |
| `_get_loan_types(company_id)` | recordset | All `employee.loan.type` for the company |
| `get_employee_loans(payslip, loan_type)` | recordset\|False | Draft installment lines in the payslip period |
| `get_employee_loans_sum(loan_type)` | dict | Sum of installments for the loan type → input |
| `action_recall_payslip_input_lines_calculation()` | True | Manual trigger to re-run `_compute_input_line_ids` |

#### OT attendance filter (used by all OT and holiday helpers)

```python
('eligible_for_overtime', '=', True)
('overtime_approval_status', '=', 'approved')
('check_in_date', '>=', date_from)
('check_in_date', '<=', date_to)
```

#### No-pay leave filter

Uses `request_date_from` / `request_date_to` (pure `Date` fields) to avoid Datetime vs Date comparison issues. Overlap condition — includes leaves that partially span the payslip period:

```python
('request_date_from', '<=', date_to)
('request_date_to', '>=', date_from)
('state', '=', 'validate')
('holiday_status_id', 'in', leave_types.ids)   # leave types mapped to work entry code NOPAY
```

#### `_compute_input_line_ids` flow

1. Clears existing inputs.
2. Calls each `_get_*` helper, appends result if truthy.
3. Iterates `employee.loan.type` records for the company, appends installment sums.
4. Appends `fixed_allowance_ids` and `fixed_deduction_ids` from the running contract.

---

### `hr.contract` — `models/hr_contract.py`

Inherits `hr.contract`. Adds three computed, stored Float fields for per-hour OT rates.

#### Fields

| Field | Type | Description |
|---|---|---|
| `baff_ot_rate_normal` | Float (computed, stored) | `wage / monthly_hours × 1.5` |
| `baff_ot_rate_double` | Float (computed, stored) | `wage / monthly_hours × 2.0` |
| `baff_ot_rate_triple` | Float (computed, stored) | `wage / monthly_hours × 3.0` |

#### Monthly hours divisor

| `ocean_voyager_emp_category` | Divisor |
|---|---|
| `staff` | 240 hours |
| `non_staff` | 200 hours |
| unset or wage = 0 | returns 0.0 |

Depends on: `wage`, `employee_id.ocean_voyager_emp_category`

#### Methods

- `_compute_baff_ot_rates()` — compute method, triggered by `@api.depends`.
- `action_recompute_baff_ot_rates()` — manual button action; calls `_compute_baff_ot_rates()`.

---

## Salary Structures

### Input Type Codes Reference

| XML ID | Code | Name | Auto-populated by |
|---|---|---|---|
| `baff_input_norm_ot_hours` | `NORM_OT_HRS` | Normal OT Hours | `_get_normal_ot_hours` |
| `baff_input_dbl_ot_hours` | `DBL_OT_HRS` | Double OT Hours | `_get_double_ot_hours` |
| `baff_input_tpl_ot_hours` | `TRPL_OT_HRS` | Triple OT Hours | `_get_triple_ot_hours` |
| `baff_input_holiday_hours` | `HOL_HRS` | Holiday Hours | `_get_holiday_count` |
| `baff_input_attendance_day_count` | `ATTND_ALLW` | Attendance Count | `_get_attendance_records` |
| `baff_input_attendance_allowance` | `ATTND_ALLW` | Attendance Allowance | contract fixed allowances |
| `baff_input_special_allowance` | `SPEC_ALLW` | Special Allowance | contract fixed allowances |
| `baff_input_salary_advance` | `SAL_ADV` | Salary Advance | contract fixed deductions |
| `baff_input_team_help` | `TEAM_HELP` | Team Help Fund | contract fixed deductions |
| `baff_input_no_pay` | `NOPAY_DED` | No Pay Deduction | contract fixed deductions |
| `baff_input_relocation_allowance` | `REl_ALW` | Relocation Allowance | placeholder (0) |
| `input_no_pay_days` | `NOPAY` | No Pay Days | `_get_no_pay_count` |
| `input_no_of_experience` | `NO_EXP` | No of Experience | `_get_no_of_experience` |
| `baff_input_leave_allowance` | `LEAVE_ALLW` | Leave Allowance | placeholder (0) |
| `baff_input_special_incentive` | `SPEC_INCNTV` | Special Incentive | contract fixed allowances |
| `baff_input_leader_allowance` | `LDR_ALLW` | Leader Allowance | contract fixed allowances |

---

### Staff Salary Structure

Category: `ocean_voyager_emp_category = staff`

| Seq | Code | Name | Category | Formula |
|---|---|---|---|---|
| 5 | `BAFF_BASIC` | Basic Salary | BASIC | `contract.wage` |
| 10 | `NORM_OT_HRS` | Normal OT Hours | — | `inputs.NORM_OT_HRS.amount or 0.0` |
| 20 | `NORM_OT_AMT` | Normal OT Amount | ALW | `inputs.NORM_OT_HRS.amount * (contract.baff_ot_rate_normal or 0.0)` |
| 33 | `HOL_AMT` | Holiday OT Amount | ALW | `inputs.HOL_HRS.amount * (contract.baff_ot_rate_normal or 0.0)` |
| 35 | `SPEC_INCNTV` | Special Incentive | ALW | `inputs.SPEC_INCNTV.amount or 0.0` |
| 40 | `ATTND_ALLW` | Attendance Allowance | ALW | `inputs.ATTND_ALLW.amount or 0.0` |
| 45 | `SPEC_ALLW` | Special Allowance | ALW | `inputs.SPEC_ALLW.amount or 0.0` |
| 50 | `SAL_ADJ` | Salary Adjustment | ALW | *(confirm rule code)* |
| 60 | `BAFF_GROSS` | Gross Salary | GROSS | `categories.BASIC + categories.ALW` |
| 70 | `SAL_ADV` | Salary Advance | DED | `inputs.SAL_ADV.amount or 0.0` |
| 80 | `NOPAY_DED` | Nopay Deduction | DED | `inputs.NOPAY.amount * (contract.wage / 30)` |
| 90 | `EPF_EE_8` | EPF Employee 8% | DED | `-1 * epf_etf_base() * 0.08` |
| 100 | `PAYE_TAX` | APIT / PAYE Tax | DED | PAYE hook |
| 105 | `SUWA_SAMP` | Suwa Sampatha | DED | *(confirm rule code)* |
| 110 | `TEAM_HELP` | Team Help Fund | DED | `inputs.TEAM_HELP.amount or 0.0` |
| 115 | `TOT_DED` | Total Deductions | — | `categories.DED` |
| 120 | `BAFF_NET` | Net Salary | NET | `categories.GROSS - categories.DED` |

> **Note**: `SAL_ADJ` and `SUWA_SAMP` rule codes need confirmation against the actual data records.

---

### Non-Staff Salary Structure

Category: `ocean_voyager_emp_category = non_staff`

| Seq | Code | Name | Category | Formula |
|---|---|---|---|---|
| 5 | `BAFF_BASIC` | Basic Salary | BASIC | `contract.wage` |
| 10 | `NORM_OT_HRS` | Normal OT Hours | — | `inputs.NORM_OT_HRS.amount or 0.0` |
| 11 | `DBL_OT_HRS` | Double OT Hours | — | `inputs.DBL_OT_HRS.amount or 0.0` |
| 12 | `TRPL_OT_HRS` | Triple OT Hours | — | `inputs.TRPL_OT_HRS.amount or 0.0` |
| 20 | `NORM_OT_AMT` | Normal OT Amount | ALW | `inputs.NORM_OT_HRS.amount * (contract.baff_ot_rate_normal or 0.0)` |
| 21 | `DBL_OT_AMT` | Double OT Amount | ALW | `inputs.DBL_OT_HRS.amount * (contract.baff_ot_rate_double or 0.0)` |
| 22 | `TRPL_OT_AMT` | Triple OT Amount | ALW | `inputs.TRPL_OT_HRS.amount * (contract.baff_ot_rate_triple or 0.0)` |
| 33 | `HOL_AMT` | Holiday OT Amount | ALW | `inputs.HOL_HRS.amount * (contract.baff_ot_rate_normal or 0.0)` |
| 36 | `LDR_ALLW` | Leader Allowance | ALW | `inputs.LDR_ALLW.amount or 0.0` |
| 40 | `ATTND_ALLW` | Attendance Allowance | ALW | `inputs.ATTND_ALLW.amount or 0.0` |
| 45 | `REl_ALW` | Relocation Payment | ALW | `inputs.REl_ALW.amount or 0.0` |
| 50 | `SAL_ADJ` | Salary Adjustment | ALW | *(confirm rule code)* |
| 60 | `BAFF_GROSS` | Gross Salary | GROSS | `categories.BASIC + categories.ALW` |
| 70 | `SAL_ADV` | Salary Advance | DED | `inputs.SAL_ADV.amount or 0.0` |
| 80 | `NOPAY_DED` | Nopay Deduction | DED | `inputs.NOPAY.amount * (contract.wage / 26)` |
| 90 | `EPF_EE_8` | EPF Employee 8% | DED | `-1 * epf_etf_base() * 0.08` |
| 100 | `PAYE_TAX` | APIT / PAYE Tax | DED | PAYE hook |
| 105 | `SUWA_SAMP` | Suwa Sampatha | DED | *(confirm rule code)* |
| 110 | `TEAM_HELP` | Team Help Fund | DED | `inputs.TEAM_HELP.amount or 0.0` |
| 115 | `TOT_DED` | Total Deductions | — | `categories.DED` |
| 120 | `BAFF_NET` | Net Salary | NET | `categories.GROSS - categories.DED` |

> **Non-Staff vs Staff differences**: Non-Staff has double and triple OT columns; nopay divisor is 26 (not 30); Leader Allowance replaces Special Incentive.

---

## Salary Sheet Wizard

### Model: `hr.salary.sheet.wizard` — `wizard/hr_salary_sheet_wizard.py`

TransientModel. Generates an `.xlsx` salary sheet for a payroll batch.

#### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `payslip_run_id` | Many2one `hr.payslip.run` | Yes | The payroll batch to report on |
| `employee_category` | Selection (`staff`/`non_staff`) | Yes | Filters payslips by `ocean_voyager_emp_category` |

#### Data helpers

| Method | Description |
|---|---|
| `_line(payslip, code)` | `abs(sum(line_ids.total))` where `line.code == code` |
| `_net(payslip, code)` | Signed `sum(line_ids.total)` — used for Net Salary |
| `_inp(payslip, code)` | `abs(sum(input_line_ids.amount))` where `input_type_id.code == code` |
| `_loan_amount(payslip)` | Resolves loan rule codes via `employee.loan.type.hr_salary_rule_id.code`, sums matching line totals |

#### Loan resolution

Loan salary rule codes are dynamic (e.g. `EMP_LOAN_{prefix}_{company_code}`). The wizard queries `employee.loan.type` for the payslip's company, collects `hr_salary_rule_id.code` for each, and sums the corresponding payslip lines. This handles any number of loan types without hardcoding codes.

#### Staff sheet columns (24)

| Col | Label | Source |
|---|---|---|
| 1 | EPF No | `employee.epf_number` |
| 2 | Name | `employee.name` |
| 3 | Designation | `employee.job_id.name` |
| 4 | Holiday Hours | `_inp('HOL_HRS')` |
| 5 | Basic Salary | `_line('BAFF_BASIC')` |
| 6 | N. OT Hours | `_inp('NORM_OT_HRS')` |
| 7 | Rate | `contract.baff_ot_rate_normal` |
| 8 | OT Amount | `_line('NORM_OT_AMT')` |
| 9 | Nopay Days | `_inp('NOPAY')` |
| 10 | Holiday Payment Amount | `_line('HOL_AMT')` |
| 11 | Special Incentive | `_line('SPEC_INCNTV')` |
| 12 | Special Allowance | `_line('SPEC_ALLW')` |
| 13 | Attendance Allowance | `_line('ATTND_ALLW')` |
| 14 | Salary Adjustment | `_line('SAL_ADJ')` |
| 15 | Gross Salary | `_line('BAFF_GROSS')` |
| 16 | Salary Advance | `_line('SAL_ADV')` |
| 17 | Loan | `_loan_amount()` |
| 18 | Suwa Sampatha | `_line('SUWA_SAMP')` |
| 19 | Team Help Fund | `_line('TEAM_HELP')` |
| 20 | E.P.F 8% | `_line('EPF_EE_8')` |
| 21 | APIT | `_line('PAYE_TAX')` |
| 22 | Nopay Amount | `_line('NOPAY_DED')` |
| 23 | Total Deductions | `_line('TOT_DED')` |
| 24 | Net Salary | `_net('BAFF_NET')` |

#### Non-Staff sheet columns (28)

| Col | Label | Source |
|---|---|---|
| 1 | EPF No | `employee.epf_number` |
| 2 | Name | `employee.name` |
| 3 | Designation | `employee.job_id.name` |
| 4 | Holiday Hours | `_inp('HOL_HRS')` |
| 5 | Basic Salary | `_line('BAFF_BASIC')` |
| 6 | N. OT Hours | `_inp('NORM_OT_HRS')` |
| 7 | Rate | `contract.baff_ot_rate_normal` |
| 8 | D. OT Hours | `_inp('DBL_OT_HRS')` |
| 9 | Rate | `contract.baff_ot_rate_double` |
| 10 | T.OT Hours | `_inp('TRPL_OT_HRS')` |
| 11 | Rate | `contract.baff_ot_rate_triple` |
| 12 | OT Amount | Sum of NORM + DBL + TRPL OT amounts |
| 13 | Nopay Days | `_inp('NOPAY')` |
| 14 | Holiday Payment | `_line('HOL_AMT')` |
| 15 | Leader Allowance | `_line('LDR_ALLW')` |
| 16 | Attendance Allowance | `_line('ATTND_ALLW')` |
| 17 | Relocation Payment | `_line('REl_ALW')` |
| 18 | Salary Adjustment | `_line('SAL_ADJ')` |
| 19 | Gross Salary | `_line('BAFF_GROSS')` |
| 20 | Salary Advance | `_line('SAL_ADV')` |
| 21 | Loan | `_loan_amount()` |
| 22 | Suwa Sampatha | `_line('SUWA_SAMP')` |
| 23 | Team Help Fund | `_line('TEAM_HELP')` |
| 24 | E.P.F 8% | `_line('EPF_EE_8')` |
| 25 | APIT | `_line('PAYE_TAX')` |
| 26 | Nopay | `_line('NOPAY_DED')` |
| 27 | Total Deductions | `_line('TOT_DED')` |
| 28 | Net Salary | `_net('BAFF_NET')` |

#### Excel layout

| Row | Content |
|---|---|
| 0 | Company name (merged, bold 14pt) |
| 1 | Report title e.g. *Staff Salary Sheet Month of January 2025* (merged, bold 12pt) |
| 2 | Column numbers 1–N (orange `#ED7D31`, white text) |
| 3 | Column labels (orange `#ED7D31`, white text, wrap) |
| 4+ | Employee data rows (sorted by employee name) |
| last | Totals row (bold, numeric columns summed) |

Column widths: EPF No = 8, Name = 24, Designation = 16, remaining = 11.

File naming: `staff_salary_sheet_<Month>_<Year>.xlsx` / `non_staff_salary_sheet_<Month>_<Year>.xlsx`

Month derived from `payslip_run.date_start.strftime('%B')`.

#### Access

- Payroll User: full CRUD on wizard.
- Payroll Manager: full CRUD on wizard.
- Menu: Payroll → Reporting → Custom Reports → Salary Sheet.

---

## Views

### `views/hr_contract_views.xml`

Inherits `hr_contract.hr_contract_view_form` (after the `centrics_hr_overtime` layer).

- Hides the `overtime_rate` field from `centrics_hr_overtime` using `position="attributes"` + `invisible="1"` on both the `<label for="overtime_rate">` and its wrapper `<div>`. Elements remain in the DOM to avoid view parse errors from the `<label for>` reference.
- Replaces the empty right column of the **Overtime Configurations** group with three rate fields (`baff_ot_rate_normal`, `baff_ot_rate_double`, `baff_ot_rate_triple`), each using the `label` + `o_row mw-50` + `/ hourly` suffix pattern from `centrics_hr_overtime`. Visibility tied to `is_eligible_for_overtime`.
- Adds a `fa-refresh` icon button that calls `action_recompute_baff_ot_rates`. Hidden when `is_eligible_for_overtime` is False.

### `views/hr_payslip_views.xml`

Payslip form view customisations (existing, unchanged by recent work).

### `views/hr_salary_sheet_wizard_views.xml`

- Form view for `hr.salary.sheet.wizard` with `payslip_run_id` and `employee_category` inputs, plus Generate Excel / Cancel footer buttons.
- `ir.actions.act_window` with `target="new"` (dialog).
- Menu items: `menu_hr_payroll_custom_reports` (parent: `hr_payroll.menu_hr_payroll_report`) → `menu_hr_salary_sheet`.

---

## Security

`security/ir.model.access.csv` — grants full CRUD on `hr.salary.sheet.wizard` to both Payroll User and Payroll Manager groups. Required for the Custom Reports menu to be visible.

---

## Reports

`reports/baff_payslip_report.xml` — custom payslip PDF report (QWeb).

---

## Known Placeholders

The following salary rule codes are referenced in the wizard but not yet confirmed in the data files:

| Code | Column | Status |
|---|---|---|
| `SAL_ADJ` | Salary Adjustment | Needs rule code confirmation |
| `SUWA_SAMP` | Suwa Sampatha | Needs rule code confirmation |

If these rules use different codes in `hr_salary_structure_data.xml`, update the corresponding `_line(payslip, ...)` calls in `_staff_row` and `_non_staff_row`.
