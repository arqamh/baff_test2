# Employee Loan Management

## Overview

The Employee Loan Management module provides a comprehensive solution for managing employee loans within Odoo 16. It enables organizations to handle the complete loan lifecycle from request to recovery, including interest calculations, installment tracking, payroll integration, and accounting entries.

## Features

### Loan Management
- **Loan Requests**: Employees can request loans with specified amounts and purposes
- **Loan Types**: Configure different loan types with varying interest rates and terms
- **Approval Workflow**: Multi-stage approval process (Draft → Submitted → Approved → Paid → In Recovery → Recovered)
- **Loan Stages**: Configurable loan stages with Kanban view support

### Interest Calculation
- **Equated Balance Method**: Fixed EMI throughout the loan tenure
- **Reducing Balance Method**: Interest calculated on outstanding principal

### Installment Management
- **Automatic Generation**: Generate installment schedules based on loan parameters
- **Flexible Scheduling**: Configure deduction start month and payroll effective month
- **Payment Tracking**: Track paid, pending, and skipped installments

### Guarantor Management
- **Multiple Guarantors**: Add multiple guarantors per loan
- **Validation Rules**: Configure minimum guarantors required and maximum loans an employee can guarantee

### Payroll Integration
- **Automatic Deductions**: Integrate with HR Payroll for automatic loan deductions
- **Salary Rules**: Create salary rules for each loan type
- **Payslip Input Types**: Configure payslip input types for loan deductions

### Accounting Integration
- **Journal Entries**: Automatic journal entry creation on loan payment
- **Configurable Accounts**: Set default receivable, payable, and interest accounts per loan type

### Reporting
- **Loan Agreement Report**: Print detailed loan agreements with installment schedules
- **Stage-based Printing**: Configure which stages allow document printing

## Configuration

### 1. Loan Stages
Navigate to: **Loan Management → Configuration → Employee Loan Stages**

Configure loan stages with:
- Stage name and sequence
- Kanban fold option
- Allow Print option (enables Print button at this stage)

### 2. Loan Types
Navigate to: **Loan Management → Configuration → Loan Types**

Configure loan types with:
- Interest rate and calculation method
- Minimum/Maximum loan amounts
- Standard number of installments
- Accounting accounts (Journal, Receivable, Payable, Interest, Bank/Cash)
- Payroll integration settings

### 3. Company Settings
Navigate to: **Settings → Loan Management**

Configure:
- Minimum guarantors required
- Maximum loans an employee can guarantee
- Basic salary as maximum loan amount option
- Payroll integration enable/disable

## Usage

### Creating a Loan Request
1. Navigate to **Loan Management → Loans**
2. Click **Create**
3. Select employee and loan type
4. Enter loan amount and number of installments
5. Specify the purpose
6. Click **Submit**

### Approving a Loan
1. Open the submitted loan
2. Click **Generate Installments** to create the installment schedule
3. Review the installment lines
4. Add guarantors if required
5. Click **Approve**

### Paying a Loan
1. Open the approved loan
2. Click **Pay** to disburse the loan
3. A journal entry is automatically created

### Printing Loan Documents
1. Configure "Allow Print" on desired loan stages
2. Open a loan at an allowed stage
3. Click **Print** button in the header

## Security Groups

- **Loan User**: Basic access to loan management features
- **Loan Manager**: Full access including approval and configuration

## Dependencies

- `base`
- `hr`
- `account_accountant`
- `hr_payroll`
- `centrics_company_standard_customizations`

## Version

16.0.1.1.0

## Author

Centrics Business Solutions (Pvt) Ltd
- Website: http://www.centrics.cloud/

## License

OPL-1 (Odoo Proprietary License)
