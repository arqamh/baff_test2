{
    'name': 'Baff Accounting Modifications',
    'sequence': 0,
    'version': '16.0.0.1',
    'license': 'LGPL-3',
    'summary': "Baff Accounting Modifications",
    'description': """ This module contains all the Accounting Modifications of the Baff""",
    'author': 'Centrics Business Solutions PVT Ltd',
    'company': 'Centrics Business Solutions PVT Ltd',
    'website': 'http://www.centrics.cloud/',
    'depends': ['base', 'account', 'account_asset'],
    'data': [
        'data/baff_accounting_modification_data.xml',
        'views/account_move.xml',
        'views/account_journal.xml'
    ],
    'demo': [
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
