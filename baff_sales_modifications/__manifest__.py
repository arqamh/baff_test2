{
    'name': 'Baff Sales Modifications',
    'sequence': 0,
    'version': '16.0.0.1',
    'license': 'LGPL-3',
    'summary': "Baff Sales Modifications",
    'author': 'Centrics Business Solutions PVT Ltd',
    'company': 'Centrics Business Solutions PVT Ltd',
    'website': 'http://www.centrics.cloud/',
    'depends': ['base', 'sale', 'sale_crm', 'baff_inventory_modifications', 'hr'],
    'data': [
        'data/ir_sequence.xml',
        'data/mail_templates.xml',
        'views/sale_order.xml',
        'views/account_move_views.xml',
    ],
    'demo': [
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
