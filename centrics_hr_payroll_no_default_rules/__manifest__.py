# -*- coding: utf-8 -*-
{
    'name': 'Payroll - No Default Salary Rules',
    'version': '16.0.1.0.0',
    'summary': 'Prevent Odoo from auto-adding default salary rules to new payroll structures.',
    'description': """
Payroll - No Default Salary Rules
=================================

Global, reusable foundation module.

Core ``hr.payroll.structure`` declares ``rule_ids`` with
``default=_get_default_rule_ids``, which injects eight generic salary rules
(Basic, Gross, Net, Deduction, Attachment/Assignment of Salary, Child Support,
Reimbursement) into every newly created Salary Structure. Implementations that
define their own complete rule set (in the UI or via XML data files) end up with
unwanted/duplicate rules.

This module overrides ``default_get`` on ``hr.payroll.structure`` to strip the
``rule_ids`` default, so a new structure starts empty. Only the rules added
explicitly end up linked to the structure. The behavior applies to both UI and
ORM/XML creation and does not modify any Odoo core file.

Install this module wherever a clean (default-free) payroll structure is
required.
""",
    'category': 'Human Resources/Payroll',
    'license': 'OPL-1',
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'http://www.centrics.cloud/',
    'depends': ['hr_payroll'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
