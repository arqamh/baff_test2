{
    'name': 'HR Attendance Extend',
    'version': '16.0.1.0.1',
    'sequence': 250,
    'category': 'Localization',
    'license': 'OPL-1',
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'http://www.centrics.cloud/',
    'summary': 'General Customizations in the HR Attendance Module',
    'description': """
    1. Allow to enter attendance by Configuration
    2. Maintain Manual Attendance Log
    3. Allow to create system attendance records from the Manual Log by cron job
    4. Cron Job to create system attendance records from the Manual Log
    """,
    'depends': [
        'base',
        'hr_attendance',
    ],
    'data': [
        'security/centrics_hr_attendance_security.xml',
        'security/centrics_hr_attendance_groups.xml',
        'security/ir.model.access.csv',
        'views/centrics_hr_attendance_menus.xml',
        'views/hr_attendance_import_configuration_views.xml',
        'views/hr_attendance_manual_log_views.xml',
        'views/attendance_manual_uploader_views.xml',
        'views/hr_attendance_views.xml',
        'data/ir_cron_data.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
