# -*- coding: utf-8 -*-

{
    'name': 'MRP Production Progress',
    'version': '16.0.1.1.0',
    'category': 'Manufacturing',
	'author': 'Centrics Business Solutions',
	'maintainer': 'Centrics Business Solutions',
	'company': 'Centrics Business Solutions',
	'website': 'http://www.centrics.cloud/',
    'summary': 'Component and operation progress tracking for manufacturing orders with child MO aggregation and sales order integration.',
    'depends': ['mrp', 'sale_mrp'],
    'data': [
        'views/mrp_production_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
