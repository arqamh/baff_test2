{
    'name': 'Employee Advance Management',
    'version': '16.0.1.0.0',
    'sequence': 1,
    'category': 'Localization',
    'license': 'OPL-1',
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'http://www.centrics.cloud/',
    'summary': 'Manage Employee Advances',
    'description': """
    1. Define the Advance Type
    """,
    'depends': [
        'base',
        'hr',
        'hr_contract',
        'account_accountant'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/centrics_hr_advance_management_menus.xml',
        'views/advance_type_views.xml',
        'views/hr_advance_request_views.xml',
        'views/res_config_settings_views.xml',
        'views/hr_contract_views.xml',
        'data/mail_template_data.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
