# -*- coding: utf-8 -*-
{
    'name': 'Ocean Voyager - HR Attendance Extend',
    'version': '16.0.1.0.0',
    'sequence': 2,
    'category': 'Human Resources/Attendances',
    'license': 'OPL-1',
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'https://www.centrics.lk',
    'summary': 'BAFF Specific Attendance Workflow Customization',
    'description': """
        1. Update Employee name get with EPF number 
        2. Allow the user to impprt attendance records by EPF number
    """,
    'depends': [
        'hr_attendance'
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/make_attendance_report_views.xml',
        'data/paperformat.xml',
        'report/attendance_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
