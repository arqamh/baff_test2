# -*- coding: utf-8 -*-
{
    'name': 'MRP Unbuild Reverse',
    'version': '16.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Reverse unbuild manufacturing orders and associated entries',
    'description': """
MRP Unbuild Reverse
===================
This module allows you to reverse completed unbuild manufacturing orders.

Features:
---------
* Reverse unbuild orders that are in 'done' state
* Automatically reverse all associated stock moves
* Reverse stock valuation layers and accounting entries
* Track reversal history with chatter messages
* New 'reversed' state for unbuild orders

When an unbuild order is reversed:
- All stock moves (consume and produce) are reversed
- Stock valuation entries are automatically reversed
- The unbuild order state changes to 'reversed'
- A message is posted to the original manufacturing order (if linked)
    """,
	'author': 'Centrics Business Solutions',
	'maintainer': 'Centrics Business Solutions',
	'company': 'Centrics Business Solutions',
	'website': 'http://www.centrics.cloud/',
    'depends': [
        'mrp',
        'stock_account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_unbuild_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
