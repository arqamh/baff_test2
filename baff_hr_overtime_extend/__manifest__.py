{
    'name': 'Ocean Voyager - HR Overtime Extend',
    'version': '16.0.1.0.0',
    'sequence': 1,
    'category': 'Human Resources/Overtime',
    'license': 'OPL-1',
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'http://www.centrics.cloud/',
    'summary': 'Extend the Overtime module as per the requirements of Ocean Voyager',
    'description': """
    """,
    'depends': [
        'base',
        'hr',
        'baff_hr_extend',
        'centrics_hr_overtime',
    ],
    'data': [
        'views/hr_attendance_views.xml',
        'views/hr_overtime_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
