# -*- coding: utf-8 -*-
{
    'name': 'PAYEE Tax for Payroll',
    'description': """
                           This module adds PAYEE tax calculation capabilities to Odoo Payroll:
                           * Configure tax brackets with below/between/above conditions
                           * Set different rates per bracket
                           * Easy integration with salary rules
                           * Automated tax calculation based on gross income
                       """,

    'summary': 'Configure PAYEE tax brackets (below/between/above) and use them in Odoo Payroll.',
    'version': '16.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'author': 'Centrics Business Solutions (Pvt) Ltd',
    'website': 'http://www.centrics.cloud/',
    'license': 'OPL-1',
    'depends': ['hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_payee_tax_views.xml',
        'views/res_config_settings_views.xml',
        'data/hr_payee_tax_data.xml'
    ],
    'application': False,
    'installable': True,
}
