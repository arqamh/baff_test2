{
    'name': 'HR Local Customizations',
    'version': '16.0.1.0.0',
    'sequence': 1,
    'category': 'Localization',
    'license': 'OPL-1',
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'http://www.centrics.cloud/',
    'summary': 'General Customizations in the HR Module',
    'description': """
    1. Employee Profile Approval Process
    """,
    'depends': [
        'base',
        'hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/centrics_hr_groups.xml',
        'security/centrics_hr_security.xml',
        'views/hr_employee_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/employee_profile_rejection_views.xml',
        'data/mail_template_data.xml',
        'data/ir_sequence_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
