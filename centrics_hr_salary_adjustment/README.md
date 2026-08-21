Salary Change Request Module
============================

This module provides a structured and auditable way to manage salary increments and decrements for employees in Odoo.

Features:
---------
* Create requests for salary increment or decrement for employees.
* Automatically load current wage, allowances, and deductions from employee contract.
* Submit request for approval and track status.
* Update contract wage, fixed allowances, and deductions upon approval.
* Maintain a detailed log of all changes in the contract.
* Support for effective date scheduling and tracking.

Usage:
------
1. Go to HR > Salary Changes > Change Requests.
2. Create a new request, select the employee, and adjust the wage or components.
3. Submit the request for approval.
4. HR manager can approve or reject the request.
5. Approved changes are reflected in the employee contract and logged in the contract history.

Security:
---------
- Only HR users (`hr.group_hr_user`) can create and manage requests.

Dependencies:
-------------
- hr_contract
- hr_payroll

License:
--------
This module is distributed under the Odoo Proprietary License v1.0.