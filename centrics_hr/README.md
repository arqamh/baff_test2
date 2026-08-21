# Centrics HR

## Overview
Enhanced HR module for Odoo 16 that extends the standard HR functionality with additional features for employee management, approval workflows, and retirement planning.

## Features

### Employee Management
- **Employee Number**: Automatic or manual employee number generation
- **Name Fields**: Enhanced name tracking with separate fields for:
  - Initials of the Name
  - First Name
  - Middle Name
  - Last Name

### Approval Workflow
- Employee profile approval process
- State management: Draft, Waiting for Approval, Approved, Rejected
- Email notifications at each approval stage
- Configurable approver assignment
- Pending employees dashboard for approvers

### Company Settings
- Enable/disable employee approval workflow
- Configure automatic employee number generation
- Set retirement age for automatic retirement date calculation

### Additional Fields
- Joined Date tracking
- Retirement Date (auto-calculated based on birthday and company retirement age)
- Approver assignment

## Configuration

### Company Settings
Navigate to Settings > Companies > Your Company to configure:
1. **Employee Approval Needed**: Toggle to enable approval workflow
2. **Employee Number Auto Generate**: Toggle to enable automatic employee numbering
3. **Retirement Age**: Set the retirement age for automatic retirement date calculation

## Usage

### Creating an Employee (with approval enabled)
1. Navigate to Employees > Employees
2. Create a new employee record
3. Fill in required information (Job Position, Mobile Phone, Work Email)
4. Click "Send for Approval"
5. Assigned approver receives email notification
6. Approver reviews and either approves or rejects
7. Requester receives email notification of decision

### Approving Employees
1. Navigate to Employees > Pending Employees
2. Review employee details
3. Click "Approve" or "Reject"
4. If rejecting, provide a reason

## Dependencies
- base
- hr
- hr_payroll

## Author
Centrics Business Solutions (Pvt) Ltd
Website: https://www.centrics.lk

## License
OPL-1

## Version
16.0.1.0.0
