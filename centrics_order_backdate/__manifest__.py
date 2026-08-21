# -*- coding: utf-8 -*-

{
    'name': 'Sale Order Backdate',
    'sequence': 0,
    'author': 'Centrics Business Solutions PVT Ltd',
    'website': 'http://www.centrics.cloud/',
    'summary': 'Sale Order Backdate',
    "version": "16.0.0",
    'author': 'Centrics Business Solutions PVT Ltd',
    'company':'Centrics Business Solutions PVT Ltd',
    'depends': ['base','sale', 'stock'],
    'license': 'LGPL-3',
    'data': [
        'data/ir_cron.xml',
        # 'security/security.xml',
        'security/ir.model.access.csv',
        'views/stock_picking.xml',
        'wizard/backdate_validate_wizard_internal.xml',

    ],
    'demo': [],
    'application': True,
    'installable': True,
    'auto_install': False,
}

