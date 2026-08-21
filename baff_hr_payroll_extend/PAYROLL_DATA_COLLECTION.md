# Payroll Verification — Customer Data Collection

Ocean Voyager HRM · `baff_hr_payroll_extend`

Use this checklist to collect all information required to reproduce and verify a monthly payroll run.
**Reference period: the most recently completed payroll month.**

---

## A. Employee Master Data

*Provide one row per employee. Collect Staff and Non-Staff lists separately.*

| # | Field | Example | Notes |
|---|-------|---------|-------|
| 1 | First name | Nimal | |
| 2 | Middle name | — | Optional |
| 3 | Last name | Perera | Required when EPF eligible |
| 4 | Name initials | N.P. | Required when EPF eligible |
| 5 | EPF number | EPF-001234 | |
| 6 | EPF registration date | 2020-01-15 | |
| 7 | EPF eligible? | Yes / No | Drives EPF 8 % / 12 % / 3 % rules |
| 8 | Occupational group | Executive / Non-Executive / Clerical | EPF classification |
| 9 | Employment type | Permanent / Contract / Trainee | EPF classification |
| 10 | Employee category | **Staff** or **Non-Staff** | Determines OT rate divisor (240 h vs 200 h) and salary structure |
| 11 | Job designation | Senior Officer | Printed on salary sheet |
| 12 | Date of joining | 2019-03-01 | Contract start boundary |

---

## B. Contract Data

*One active contract per employee must exist and be in **Running** state for the payroll month.*

| # | Field | Example | Notes |
|---|-------|---------|-------|
| 1 | Monthly basic wage (LKR) | 50,000.00 | Base for `BAFF_BASIC` and OT rate computation |
| 2 | Contract start date | 2019-03-01 | Must be on or before the payroll period start |
| 3 | Contract status | Running | Only `open` contracts are computed |
| 4 | Salary structure | **Staff** or **Non-Staff** | Selects the correct rule set |
| 5 | Eligible for overtime? | Yes / No | Enables OT input auto-population |

> **OT rates are computed automatically** from the wage and category — no manual entry needed.
> Staff: `wage ÷ 240 × multiplier`. Non-Staff: `wage ÷ 200 × multiplier`.

---

## C. Fixed Allowances & Deductions on Contract

*These are recurring monthly amounts configured on the contract. Provide the amount for each that applies.*

### Allowances

| # | Allowance Type | Applies To | Input Code | Amount (LKR) |
|---|----------------|-----------|------------|--------------|
| 1 | Special Incentive | Staff only | `SPEC_INCNTV` | __________ |
| 2 | Attendance Allowance | Both | `ATTND_ALLW` | __________ |
| 3 | Leader Allowance | Non-Staff only | `LDR_ALLW` | __________ |
| 4 | Special Allowance | Both (if any) | `SPEC_ALLW` | __________ |
| 5 | Relocation Payment | Non-Staff (if any) | `REL_ALLW` | __________ |

### Deductions

| # | Deduction Type | Applies To | Input Code | Value |
|---|----------------|-----------|------------|-------|
| 6 | No-Pay days for the month | Both | `NOPAY_DED` | __ days |

> **No-Pay formula**: `days × (wage ÷ 30)` for Staff; `days × (wage ÷ 26)` for Non-Staff.
> Provide the number of days as a decimal (e.g. `2.0`), not just whether a leave exists.

---

## D. Attendance & Overtime Records

*For the payroll month — list every date on which OT was worked, per employee.*

| # | Field | Notes |
|---|-------|-------|
| 1 | Employee name | |
| 2 | Date of OT attendance | e.g. 2026-03-10 |
| 3 | Normal OT hours | ×1.5 rate — Staff and Non-Staff |
| 4 | Double OT hours | ×2.0 rate — **Non-Staff only** |
| 5 | Triple OT hours | ×3.0 rate — **Non-Staff only** |
| 6 | Holiday hours | Holiday payment — both |
| 7 | OT approval status | Must be **Approved** to populate payslip |

> A single employee may have multiple attendance records in a month.
> Provide totals per employee if individual dates are not available, noting the approval status.

### Summary table (per employee)

| Employee | Norm OT Hrs | Dbl OT Hrs | Trpl OT Hrs | Holiday Hrs | Status |
|----------|------------|------------|-------------|-------------|--------|
| | | | | | Approved |
| | | | | | Approved |

---

## E. Leave / No-Pay Records

*For the payroll month — only **validated** no-pay leaves feed the payslip.*

| # | Field | Notes |
|---|-------|-------|
| 1 | Employee name | |
| 2 | Leave type | Must be linked to the **NOPAY** work entry type |
| 3 | Leave from date | e.g. 2026-03-05 |
| 4 | Leave to date | e.g. 2026-03-06 |
| 5 | Number of no-pay days | e.g. 2 |
| 6 | Approval status | Must be **Validated** |

> The validated leave count populates the informational `NOPAY` payslip input only.
> The actual salary deduction is driven by the **contract fixed deduction** (Section C row 6).
> Both must match for the payslip to be correct.

---

## F. Loan Deductions

*Per employee with an active loan being deducted this month.*

| # | Field | Example | Notes |
|---|-------|---------|-------|
| 1 | Loan type name | Staff Welfare Loan | Determines which salary rule deducts it |
| 2 | Loan status | In Recovery | Must be **Paid** or **In Recovery** |
| 3 | Installment month / year | March 2026 | Must match the payroll period |
| 4 | Installment amount (LKR) | 5,000.00 | Capital + interest for this month |
| 5 | Payment method | Payroll | Only `payroll` installments deduct via payslip |
| 6 | Installment status | Draft | Already-paid installments will not deduct again |

---

## G. One-Off / Variable Inputs

*For the payroll month — amounts not on the contract; entered per payslip.*

| # | Input | Code | Amount (LKR) | Notes |
|---|-------|------|--------------|-------|
| 1 | Salary Advance | `SAL_ADV` | __________ | Deducted from net |
| 2 | Suwa Sampatha | `SUWA_SAMP` | __________ | Insurance / welfare fund deduction |
| 3 | Team Help Fund | `TEAM_HELP` | __________ | |
| 4 | Salary Adjustment | `SAL_ADJ` | __________ | One-off correction — can be positive or negative |

*Leave blank if not applicable for the month.*

---

## H. EPF / ETF Configuration

*Company-level settings — verify once, not per payslip.*

| # | Setting | Expected Value | Rule Code |
|---|---------|---------------|-----------|
| 1 | EPF employee contribution | 8 % | `EPF_EE_8` |
| 2 | EPF employer contribution | 12 % | `EPF_ER_12` |
| 3 | ETF employer contribution | 3 % | `EPF_ER_3` |
| 4 | APIT / PAYE tax | Formula-based or fixed amount | `PAYE_TAX` |

> Confirm whether APIT is being computed by the system or entered manually as a fixed amount.

---

## I. Actual Payslip Output for Comparison

*This is what the system output will be checked against.*

| # | Document / Data | Format |
|---|-----------------|--------|
| 1 | Signed or approved payslip for each employee | PDF or printed copy |
| 2 | Salary sheet for the month | Excel or PDF — shows all employees in one view |
| 3 | Per-employee breakdown: Basic, each allowance, each deduction, Gross, Net | |
| 4 | Total payroll summary: sum of Gross / EPF EE / EPF ER / ETF / Net | |
| 5 | Bank transfer list or payment voucher | To verify net amounts actually paid |
| 6 | EPF Form C for the month | To verify total EPF contributions |
| 7 | ETF payment schedule for the month | To verify total ETF contributions |

---

## J. Quick Reference — Salary Rule Codes

| Code | Description | Structure |
|------|-------------|-----------|
| `BAFF_BASIC` | Basic Salary | Both |
| `NORM_OT_AMT` | Normal OT Amount | Both |
| `DBL_OT_AMT` | Double OT Amount | Non-Staff |
| `TRPL_OT_AMT` | Triple OT Amount | Non-Staff |
| `HOL_AMT` | Holiday Payment | Both |
| `SPEC_INCNTV` | Special Incentive | Staff |
| `SPEC_ALLW` | Special Allowance | Both |
| `ATTND_ALLW` | Attendance Allowance | Both |
| `LDR_ALLW` | Leader Allowance | Non-Staff |
| `REL_ALLW` | Relocation Payment | Non-Staff |
| `SAL_ADJ` | Salary Adjustment | Both |
| `BAFF_GROSS` | Gross Salary | Both |
| `SAL_ADV` | Salary Advance | Both |
| `SUWA_SAMP` | Suwa Sampatha | Both |
| `TEAM_HELP` | Team Help Fund | Both |
| `EPF_EE_8` | EPF Employee 8 % | Both |
| `PAYE_TAX` | APIT / PAYE Tax | Both |
| `NOPAY_DED` | No-Pay Deduction | Both |
| `TOT_DED` | Total Deductions | Both |
| `BAFF_NET` | Net Salary | Both |
| `EPF_ER_12` | EPF Employer 12 % | Both |
| `EPF_ER_3` | ETF Employer 3 % | Both |

---

## K. Minimum Data Required Per Employee — Summary

```
Employee     name · initials · last name · EPF number · category (Staff / Non-Staff)
Contract     wage · structure · OT eligibility
Attendance   approved OT hours by type (Normal / Double / Triple / Holiday) for the month
No-Pay       number of no-pay days for the month
Allowances   SPEC_INCNTV / LDR_ALLW / ATTND_ALLW amounts from contract
Loans        installment amount + loan type (if any deduction this month)
Variables    Salary Advance · Suwa Sampatha · Team Help Fund · Salary Adjustment (if any)
Reference    actual payslip or salary sheet for comparison
```

---

*Document maintained alongside `baff_hr_payroll_extend` — Ocean Voyager Payroll Extensions.*
