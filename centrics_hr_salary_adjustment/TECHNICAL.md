Technical Mapping Document
==========================

Models:
-------
1. `hr.salary.change.request`
   - Tracks salary change request.
   - Contains wage and salary rule references.
   - States: draft, submitted, approved, rejected.

2. `salary.change.request.line`
   - Linked to `hr.salary.change.request`.
   - Holds type (allowance/deduction), rule, and amount changes.

3. `hr.contract.log`
   - Tracks historical wage/allowance/deduction updates.
   - Linked to contract and request record.

Fields:
-------
- Employee selection triggers auto-fetch of wage/contract/salary lines.
- Manual entry of new wage, updated amounts.

Actions:
--------
- `action_submit`: Moves request to submitted state.
- `action_approve`: Updates contract and logs changes.
- `action_reject`: Marks request as rejected.

Views:
------
- Form View: Full editable form with dynamic load and notebook.
- Tree View: Summary of requests.
- Menu: Under HR > Salary Changes.

Security:
---------
- Access rules for `hr.group_hr_user` only.

Dependencies:
-------------
- Requires allowance/deduction tracking in `hr.contract` (custom or studio).

Future Enhancements:
---------------------
- Cron to apply changes on `effective_date`.
- Email notifications.
- Group-based approval workflow.
- Change preview button before approval.