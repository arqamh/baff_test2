{
    'name': 'HR Multiple Education Qualifications',
    'version': '16.0.1.0.0',
    'sequence': 1,
    'category': 'Human Resources',
    'license': 'OPL-1',
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'http://www.centrics.cloud/',
    'summary': 'Multiple Education Qualifications in the HR Module',
    'description': """
    1. Allow user to enable and disable Multiple Education Qualification
    2. Hide the default Educational Qualifications in the Employee Form 
    3. Add new tab into the Employee Form for Multiple Education Qualification
    """,
    'depends': [
        'base',
        'hr',
        'centrics_hr'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/certification_level_views.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
