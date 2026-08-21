# -*- coding: utf-8 -*-
{
    'name': 'Ocean Voyager - Hr Extend',
    'version': '16.0.1.0.0',
    'summary': 'HR Module Extends for the BAFF',
    'description': '''
        Detailed description of the module
    ''',
    'category': 'Human Resources/Employees',
    'author': 'Centrics Business Solutions (Pvt) Ltd',
    'company': 'Centrics Business Solutions (Pvt) Ltd',
    'maintainer': 'Centrics Business Solutions (Pvt) Ltd',
    'website': 'https://www.centrics.lk',
    'depends': ['base', 'mail', 'centrics_hr', 'centrics_hr_provident_fund'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_views..xml'
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}