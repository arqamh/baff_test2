# Changelog — baff_hr_payroll_extend

All notable changes to this module are recorded here.
Format: `[version] YYYY-MM-DD — description`

---

## [18.0.1.0.9] — 2026-06-22

### Changed
- **Default salary rule prevention provided by a dedicated module**:
  - Added the new reusable foundation module
    `centrics_hr_payroll_no_default_rules` to `depends`. It overrides
    `hr.payroll.structure.default_get` to drop the `rule_ids` default
    (`_get_default_rule_ids`), so new structures are created with no auto-added
    generic salary rules (BASIC, GROSS, DEDUCTION, ATTACH_SALARY, ASSIG_SALARY,
    CHILD_SUPPORT, REIMBURSEMENT, NET).
  - The prevention behavior lives in that module (not here) so it can be reused
    across payroll implementations.

### Migration
- **`migrations/18.0.1.0.8/post-migration.py`** — one-off cleanup of structures
  polluted by earlier installs:
  - Deletes salary rules linked to the three BAFF structures whose `code` is one
    of the eight core default codes **and** which carry no external ID (i.e.
    runtime-injected, not XML-defined).
  - XML-defined `BAFF_*` rules (all carry an external ID) are never touched.
  - Action is logged (count, codes, structure names).

## [18.0.1.0.7] — 2026-04-05

### Fixed
- **Wizard `_non_staff_row` — Relocation Payment always 0**
  (`wizard/hr_salary_sheet_wizard.py`):
  - `self._line(payslip, 'REl_ALW')` used a mixed-case code that never matched
    the salary rule. Corrected to `self._line(payslip, 'REL_ALLW')`.

## [18.0.1.0.6] — 2026-04-05

### Added
- **Salary Sheet Excel report** (`wizard/hr_salary_sheet_wizard.py`,
  `views/hr_salary_sheet_wizard_views.xml`):
  - New transient model `hr.salary.sheet.wizard` with two inputs:
    - `payslip_run_id` — selects the payroll batch (`hr.payslip.run`)
    - `employee_category` — selects Staff or Non Staff
  - Generates an `.xlsx` file via `xlsxwriter` and returns it as a download.
  - **Staff sheet** — 24 columns: EPF No, Name, Designation, Holiday Hours,
    Basic Salary, N. OT Hours, Rate, OT Amount, Nopay Days, Holiday Payment
    Amount, Special Incentive, Special Allowance, Attendance Allowance, Salary
    Adjustment, Gross Salary, Salary Advance, Loan, Suwa Sampatha, Team Help
    Fund, E.P.F 8%, APIT, Nopay Amount, Total Deductions, Net Salary.
  - **Non-Staff sheet** — 28 columns: EPF No, Name, Designation, Holiday Hours,
    Basic Salary, N. OT Hours + Rate, D. OT Hours + Rate, T.OT Hours + Rate,
    OT Amount, Nopay Days, Holiday Payment, Leader Allowance, Attendance
    Allowance, Relocation Payment, Salary Adjustment, Gross Salary, Salary
    Advance, Loan, Suwa Sampatha, Team Help Fund, E.P.F 8%, APIT, Nopay,
    Total Deductions, Net Salary.
  - Loan amount resolved dynamically from `employee.loan.type.hr_salary_rule_id`
    per company — works for any number of loan types.
  - File naming: `staff_salary_sheet_<Month>_<Year>.xlsx` /
    `non_staff_salary_sheet_<Month>_<Year>.xlsx`.
  - Excel formatting: company name title row, report subtitle, orange
    (`#ED7D31`) numbered + labelled header rows, totals row.
- **Security** (`security/ir.model.access.csv`):
  - `access_hr_salary_sheet_wizard_user` — Payroll User: full CRUD on wizard.
  - `access_hr_salary_sheet_wizard_manager` — Payroll Manager: full CRUD on wizard.
- **Menu** (`views/hr_salary_sheet_wizard_views.xml`):
  - New submenu **Custom Reports** under Payroll → Reporting.
  - **Salary Sheet** action under Custom Reports opens the wizard in a dialog.

## [18.0.1.0.5] — 2026-04-05

### Added
- **OT rate computed fields** on `hr.contract` (`models/hr_contract.py`):
  - `baff_ot_rate_normal`, `baff_ot_rate_double`, `baff_ot_rate_triple` converted
    from plain `Float` fields to `@api.depends` computed fields (`store=True`).
  - Depends on `wage` and `employee_id.ocean_voyager_emp_category`.
  - Monthly hours divisor: **240** for `staff`, **200** for `non_staff`.
  - Formulas: `wage / monthly_hours × 1.5 / 2.0 / 3.0` respectively.
  - Returns `0.0` when category is unset or wage is zero.
  - `action_recompute_baff_ot_rates()` action method added for manual recomputation.
- **Contract form view** (`views/hr_contract_views.xml`):
  - New view inheritance `hr.contract.view.form.inherit.baff.hr.payroll.extend`.
  - `overtime_rate` field (from `centrics_hr_overtime`) hidden via
    `position="attributes"` — label and wrapper div both set `invisible="1"`.
  - Three computed rate fields displayed in the empty right column of the
    **Overtime Configurations** group using the same `label` + `o_row mw-50`
    pattern as `overtime_rate`; visibility tied to `is_eligible_for_overtime`.
  - `fa-refresh` icon button (`action_recompute_baff_ot_rates`) added below the
    rate fields; hidden when `is_eligible_for_overtime` is False.
- `baff_hr_extend` added to `depends` in `__manifest__.py` (required for
  `ocean_voyager_emp_category` field access).

### Changed
- **OT amount salary rules** (`data/hr_salary_structure_data.xml`) — both Staff
  and Non-Staff structures:
  - `NORM_OT_AMT`: `hours × (wage/240×1.5)` → `hours × contract.baff_ot_rate_normal`
  - `DBL_OT_AMT`: `hours × (wage/240×2)` → `hours × contract.baff_ot_rate_double`
  - `TRPL_OT_AMT`: `hours × (wage/240×3)` → `hours × contract.baff_ot_rate_triple`
  - Staff and Non-Staff rules are now identical; the category divisor (240 vs 200)
    is encapsulated in the contract computed fields.

## [18.0.1.0.4] — 2026-04-05

### Added
- Leader Allowance — Non-Staff structure only (`data/hr_payslip_input_types.xml`,
  `data/hr_salary_structure_data.xml`):
  - **Input type** `baff_input_leader_allowance` (code `LDR_ALLW`) added to
    `hr_payslip_input_types.xml`.
  - **`fixed.allowance.deduction` master record** `fixed_allowance_deduction_leader_allowance`
    created, pointing to the `LDR_ALLW` input type — enables the type to appear in
    contract fixed-allowance configuration.
  - **Salary rule** `baff_non_staff_hr_salary_rule_leader_allowance` added to the
    Non-Staff structure at sequence 36 (between Holiday OT at 33 and Attendance
    Allowance at 40), category `ALW`, formula `inputs.LDR_ALLW.amount or 0.0`.

## [18.0.1.0.3] — 2026-04-05

### Added
- Special Incentive — Staff structure only (`data/hr_payslip_input_types.xml`,
  `data/hr_salary_structure_data.xml`):
  - **Input type** `baff_input_special_incentive` (code `SPEC_INCNTV`) added to
    `hr_payslip_input_types.xml`.
  - **`fixed.allowance.deduction` master record** `fixed_allowance_deduction_special_incentive`
    created, pointing to the `SPEC_INCNTV` input type — enables the type to appear in
    contract fixed-allowance configuration.
  - **Salary rule** `baff_staff_hr_salary_rule_special_incentive` added to the Staff
    structure at sequence 35 (between Holiday OT at 33 and Attendance Allowance at 40),
    category `ALW`, formula `inputs.SPEC_INCNTV.amount or 0.0`.
  - Gross Salary (`BAFF_GROSS`) picks this up automatically via `categories.ALW` —
    no change required to that rule.

## [18.0.1.0.2] — 2026-04-05

### Changed
- `NOPAY_DED` salary rule in `data/hr_salary_structure_data.xml`:
  - **Staff** (`baff_staff_hr_salary_rule_nopay`): formula updated to
    `inputs.NOPAY_DED.amount * (contract.wage / 30)` (30-day divisor).
  - **Non-Staff** (`baff_non_staff_hr_salary_rule_nopay`): formula updated to
    `inputs.NOPAY_DED.amount * (contract.wage / 26)` (26-day divisor).
  - Previously both rules used `inputs.NOPAY_DED or 0.0` which did not compute
    the per-day rate against the contract wage.

### Fixed
- `_get_holiday_count` in `models/hr_payslip.py`:
  - **Always returned 0** — reimplemented to query `hr.attendance` records and sum
    `holiday_hours`, identical pattern to `_get_normal_ot_hours`.
  - **Missing parameters** — signature changed from `_get_holiday_count()` to
    `_get_holiday_count(employee_id, date_from, date_to)`.
  - Filters: `eligible_for_overtime = True`, `overtime_approval_status = approved`,
    `check_in_date` within the payslip date range.
  - Call site in `_compute_input_line_ids` updated to pass
    `payslip.employee_id`, `payslip.date_from`, `payslip.date_to`.
- `_get_no_pay_count` in `models/hr_payslip.py`:
  - **Was counting leave records instead of days** — replaced `search_count` with
    `search` + `sum(number_of_days)` so the result reflects actual no-pay days, not
    the number of leave requests.
  - **Silent drop of leaves ending on the last day of the payslip period** — the old
    `('date_to', '<=', date_to)` filter compared a `Datetime` value against a `Date`,
    which Odoo converts to `00:00:00`, excluding any leave whose `date_to` time was
    later in the day. Fixed by switching to `request_date_from` / `request_date_to`
    (`Date` fields), which match the payslip date fields exactly.
  - **Leaves straddling the payslip boundary were excluded** — replaced the
    "fully contained" condition with an overlap condition
    (`request_date_from <= date_to AND request_date_to >= date_from`) so leaves
    that partially fall within the payslip period are counted.
