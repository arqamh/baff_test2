{
    'name': 'Employee Provident Fund',
    'version': '16.0.1.0.0',
    'sequence': 2,
    'category': 'Human Resources/Payroll',
    'license': 'OPL-1',
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'https://www.centrics.lk',
    'summary': '',
    'description': """
    
    """,
    'depends': [
        'base',
        'hr',
        'centrics_hr',
        'hr_payroll',
        'centrics_hr_payroll'
    ],
    'data': [
       'security/ir.model.access.csv',
       'views/occupational_group_views.xml',
       'views/epf_employment_type_views.xml',
       'views/hr_employee_views.xml',
       'views/res_company_views.xml',
       'views/hr_salary_rule_views.xml',
       'wizard/epf_contribution_report_wizard_views.xml',
       'wizard/etf_contribution_report_wizard_views.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
