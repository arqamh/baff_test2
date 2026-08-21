{
    'name': 'Employee Loan Management',
    'version': '16.0.1.0.0',
    'sequence': 1,
    'category': 'Human Resources',
    'license': 'OPL-1',
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'http://www.centrics.cloud/',
    'summary': 'Comprehensive Employee Loan Management System',
    'description': """
Employee Loan Management
========================

This module provides a comprehensive solution for managing employee loans including:

* Loan requests and approval workflow
* Multiple loan types with configurable interest rates
* Equated and Reducing balance calculation methods
* Automatic installment schedule generation
* Guarantor management with validation rules
* Payroll integration for automatic deductions
* Accounting integration with journal entries
* Printable loan agreement reports
* Stage-based workflow with Kanban view
   """
    ,
    'depends': [
        'base',
        'hr',
        'centrics_company_standard_customizations',
        'account_accountant',
        'hr_payroll'
    ],
    'data': [
        'security/centrics_hr_loan_management_security.xml',
        'security/centrics_hr_loan_management_groups.xml',
        'security/ir.model.access.csv',
        'views/centrics_hr_loan_management_menus.xml',
        'views/res_config_settings_views.xml',

        'views/employee_loan_stage_views.xml',
        'views/employee_loan_type_views.xml',
        'views/employee_loan_views.xml',
        'views/employee_loan_manually_settlement_views.xml',
        # 'views/employee_loan_installment_skip_views.xml',
        'report/employee_loan_report.xml',
        'data/employee_loan_stage_data.xml',
        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
