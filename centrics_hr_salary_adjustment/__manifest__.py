{
    'name': 'Salary Increments/Decrements Management',
    'version': '16.0.1.0.0',
    'summary': 'Manage Employee Salary Adjustments effectively',
    'description': '''A module to manage and track salary increments for employees.''',
    'category': 'Human Resources',
    'author': 'Your Company',
    'license': 'OPL-1',
    'depends': ['base','hr_payroll','centrics_hr_allowance_deduction','hr_work_entry_contract_enterprise' ],
    'data': [
        'security/ir.model.access.csv',
        'views/salary_adjustment_request_menus.xml',
        'views/salary_adjustment_request_views.xml'
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
