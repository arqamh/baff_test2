# Technical Documentation - Employee Loan Management

## Module Structure

```
centrics_hr_loan_management/
├── __init__.py
├── __manifest__.py
├── README.md
├── doc/
│   └── TECHNICAL.md
├── data/
│   ├── employee_loan_stage_data.xml
│   ├── ir_sequence_data.xml
│   └── mail_template_data.xml
├── models/
│   ├── __init__.py
│   ├── employee_loan.py
│   ├── employee_loan_stage.py
│   ├── employee_loan_type.py
│   ├── employee_loan_installment_line.py
│   ├── employee_loan_guarantor.py
│   ├── employee_loan_manually_settlement.py
│   ├── employee_loan_installment_skip.py
│   ├── hr_salary_rule.py
│   ├── hr_payslip.py
│   ├── res_company.py
│   └── res_config_settings.py
├── report/
│   └── employee_loan_report.xml
├── security/
│   ├── centrics_hr_loan_management_groups.xml
│   ├── centrics_hr_loan_management_security.xml
│   └── ir.model.access.csv
├── views/
│   ├── centrics_hr_loan_management_menus.xml
│   ├── employee_loan_views.xml
│   ├── employee_loan_stage_views.xml
│   ├── employee_loan_type_views.xml
│   ├── employee_loan_manually_settlement_views.xml
│   └── res_config_settings_views.xml
└── wizard/
    └── __init__.py
```

## Data Models

### employee.loan
Main model for loan records.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Loan number (auto-generated) |
| `employee_id` | Many2one | Reference to hr.employee |
| `loan_type` | Many2one | Reference to employee.loan.type |
| `loan_amount` | Float | Requested loan amount |
| `processed_amount` | Float | Approved/processed amount |
| `interest_rate` | Float | Interest rate (from loan type) |
| `number_of_installments` | Integer | Number of monthly installments |
| `calculation_type` | Selection | 'equated_balance' or 'reducing_balance' |
| `loan_status` | Selection | Current status of the loan |
| `loan_stage_id` | Many2one | Reference to employee.loan.stage |
| `is_allow_print` | Boolean | Related field from stage for print permission |
| `deduct_from_payroll` | Selection | Month to start deductions |
| `payroll_effective_month` | Selection | Actual payroll effective month |
| `employee_loan_installment_line_ids` | One2many | Installment lines |
| `loan_guarantor_ids` | One2many | Guarantor records |

**Key Methods:**
- `action_submit_loan()`: Submit loan for approval
- `action_approve_loan()`: Approve the loan
- `action_reject_loan()`: Reject the loan
- `action_pay_loan()`: Disburse the loan and create journal entry
- `action_generate_loan_installment_lines()`: Generate installment schedule
- `action_print_loan()`: Print loan document
- `_compute_loan_stage_id()`: Compute stage from status
- `_inverse_loan_stage_id()`: Update status from stage (Kanban drag)

### employee.loan.stage
Configurable loan stages for workflow and Kanban view.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Stage name |
| `sequence` | Integer | Stage order |
| `fold` | Boolean | Folded in Kanban view |
| `allow_print` | Boolean | Allow printing at this stage |

### employee.loan.type
Loan type configuration.

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Loan type name |
| `loan_sequence_prefix` | Char | Prefix for loan numbers |
| `loan_sequence_id` | Many2one | Reference to ir.sequence |
| `is_interest` | Boolean | Has interest |
| `loan_interest` | Float | Annual interest rate |
| `standard_number_of_installments` | Integer | Default installment count |
| `is_minimum_loan_amount` | Boolean | Enable minimum validation |
| `minimal_loan_amount` | Float | Minimum loan amount |
| `is_maximum_loan_amount` | Boolean | Enable maximum validation |
| `maximal_loan_amount` | Float | Maximum loan amount |
| `default_pay_journal_id` | Many2one | Default payment journal |
| `default_receivable_account_id` | Many2one | Receivable account |
| `default_payable_account_id` | Many2one | Payable account |
| `default_interest_account_id` | Many2one | Interest income account |
| `default_bank_cash_account_id` | Many2one | Bank/Cash account |
| `hr_salary_rule_id` | Many2one | Linked salary rule |
| `hr_payslip_input_type_id` | Many2one | Linked payslip input type |

**Key Methods:**
- `action_generate_loan_sequence()`: Create IR sequence for loan type
- `action_create_payslip_input_type()`: Create payslip input type
- `action_create_salary_rule()`: Create salary rule for payroll deduction

### employee.loan.installment.line
Individual installment records.

| Field | Type | Description |
|-------|------|-------------|
| `employee_loan_id` | Many2one | Parent loan |
| `employee_id` | Many2one | Employee reference |
| `installment_ref_number` | Char | Installment reference |
| `year` | Integer | Year of installment |
| `month` | Selection | Month of installment |
| `capital_amount` | Float | Principal portion |
| `interest_amount` | Float | Interest portion |
| `installment_amount` | Float | Total EMI amount |
| `running_balance` | Float | Outstanding balance |
| `paid_capital_amount` | Float | Capital paid |
| `paid_interest_amount` | Float | Interest paid |
| `status` | Selection | 'draft', 'paid', 'skip' |
| `payment_method` | Selection | 'payroll', 'manual', 'mixed' |

### employee.loan.guarantor
Loan guarantor records.

| Field | Type | Description |
|-------|------|-------------|
| `employee_loan_id` | Many2one | Parent loan |
| `employee_id` | Many2one | Guarantor employee |
| `job_id` | Many2one | Job position |
| `department_id` | Many2one | Department |

## Interest Calculation Methods

### Equated Balance (EMI)
```python
EMI = P × r × (1 + r)^n / ((1 + r)^n - 1)

Where:
P = Principal amount
r = Monthly interest rate (annual rate / 12 / 100)
n = Number of installments
```

### Reducing Balance
```python
Interest = Outstanding Balance × (Annual Rate / 12 / 100)
Principal = Fixed Capital Amount (Loan Amount / Number of Installments)
```

## Workflow States

```
draft → submitted → approved → paid → in_recovery → recovered
                 ↘ rejected
```

## Security

### Groups
- `group_loan_user`: Basic loan operations
- `group_loan_manager`: Full access including approvals

### Record Rules
Defined in `centrics_hr_loan_management_security.xml`

## Reports

### Employee Loan Report
- Template ID: `employee_loan_template`
- Report Action ID: `action_report_employee_loan`
- Paper Format: `paperformat_employee_loan` (Custom A4 with minimal margins)

**Report Sections:**
1. Company Information
2. Employee Information
3. Loan Agreement Details
4. Loan Installments Table (with right-aligned amounts, 2 decimal places)
5. Guarantors Information
6. Approval Information

## Email Templates

Located in `data/mail_template_data.xml`:
- Employee request submission notification
- Manager approval notification
- Loan approved notification
- Loan rejected notification
- Loan granted notification

## Integration Points

### Payroll Integration
- Creates `hr.payslip.input.type` for each loan type
- Creates `hr.salary.rule` for automatic deductions
- Salary rule uses Python code to calculate deduction from payslip inputs

### Accounting Integration
- Creates `account.move` on loan disbursement
- Debits receivable account
- Credits bank/cash account

## Changelog

### Version 16.0.1.1.0
- Added `allow_print` field to `employee.loan.stage`
- Added `is_allow_print` related field to `employee.loan`
- Added Print button to loan form view (visible based on stage configuration)
- Added `action_print_loan()` method
- Added custom paper format for loan report
- Updated loan report: right-aligned financial amounts with 2 decimal places
- Updated stage views to include `allow_print` field

### Version 16.0.1.0.0
- Initial release
