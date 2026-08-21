{
    'name': "ODOO Google Connector",
    'summary': """
        Google Apps (Gmail, Calendar, Task, GDrive, Contacts) 
        Integration help out to synchronize data with ODOO including customise automation options.
    """,
    'description': """
        Synchronization of ODOO with Google Apps.
        Once data created in Google account, will be reflected in ODOO by justone click.
        It will provide customise automation options.
    """,

    'author': "WoadSoft",
    'website': "https://woadsoft.com/",
    'category': 'Sale',
    'version': '2.0',
    'depends': ['base', 'mail', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/google_credentials_views.xml',
        'views/google_connector_views.xml',
        'views/google_import_stats_views.xml',
        'views/google_export_stats_views.xml',
        'views/cron_settings_views.xml',
        'views/res_partner_views.xml',
        'views/calendar_event_views.xml',
        'views/menus.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'external_dependencies': {
        'python': [],
    },
    'price': 300,
    'currency': 'EUR',
    'license': 'OPL-1',
    'images': ["images/banner.gif"],
    'application': True
}
