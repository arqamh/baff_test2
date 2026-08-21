{
    'name': 'Inventory At Date Report',
    'version': '16.0.1.0.0',
    'sequence': 1,
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'http://www.centrics.cloud/',
    'summary': 'Inventory At Date Report',
    'description': """Inventory At Date Report""",
    'license': 'LGPL-3',
    'depends': [
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizards/inventory_at_date_report_wizard.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}