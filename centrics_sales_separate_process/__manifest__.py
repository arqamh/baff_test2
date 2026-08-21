{
    'name': 'Centrics Sales Separate Process',
    'sequence': 0,
    'version': '16.0.0.1',
    'license': 'LGPL-3',
    'summary': "Centrics Sales Separate Process",
    'description': """This module contains all the separations of sales order""",
    'author': 'Centrics Business Solutions PVT Ltd',
    'company': 'Centrics Business Solutions PVT Ltd',
    'website': 'http://www.centrics.cloud/',
    'depends': ['base', 'crm', 'sale', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_templates.xml',
        'views/sale_order.xml',
        'views/invoiceable_lines_views.xml',
    ],
    'demo': [
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
