{
    'name': 'Payroll Localization',
    'version': '16.0.1.0.0',
    'sequence': 2,
    'category': 'Localization',
    'license': 'OPL-1',
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'https://www.centrics.lk',
    'summary': 'Manage Employee Payroll',
    'description': """
    

    """,
    'depends': [
        'base',
        'hr',
        'hr_payroll',
        'hr_payroll_account',
        'centrics_hr',
        'centrics_hr_attendance'
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_salary_rule_views.xml'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
