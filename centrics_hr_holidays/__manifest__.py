{
    'name': 'Time Off Localization',
    'version': '16.0.1.0.0',
    'sequence': 2,
    'category': 'Localization',
    'license': 'OPL-1',
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'https://www.centrics.lk',
    'summary': 'Extend the Time Off module with Localizations',
    'description': """
    """,
    'depends': [
        'hr_payroll',
        'hr_holidays',
    ],
    'data': [
        'data/hr_leave_data.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
