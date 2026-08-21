# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name': "Delivery Stock Restriction compare to Order/Demand Quantity",
    'version': '16.0.0.0',
    'category': 'Warehouse',
    'summary': "Product Block Quantity Stock Block Quantity Inventory Stock Warehouse Qty Lock Manufacturing Demand Quantity Stock Inventory Quantity Block Auto Block Stock Qty Stock Delivery Quantity Block Delivery Quantity Block Inventory Demand Qty Restrict Deliver Qty",
    'description': """
        Stock Block Quantity Odoo App helps users to allow or block transfer orders/receipt/delivery/manufacturing orders where done quantities are bigger than the requested quantities. If user allow stock picking/receipt/delivery/manufacturing orders on exceeded quantity checkbox, It will allow to validating picking where done qty is greater than demanded qty otherwise block picking/receipt/delivery/manufacturing orders and raised validation error.
    """,
    'author': 'BROWSEINFO',
    "price": 12,
    "currency": 'EUR',
    'website': 'https://www.browseinfo.com/demo-request?app=bi_stock_block_quantity&version=16&edition=Community',
    'depends': ['base','sale_management','purchase','stock','mrp'],
    'data': [
        'views/stock_picking_type_views.xml',
        'views/mrp_bom_views.xml',
    ],
    'license':'OPL-1',
    'installable': True,
    'auto_install': False,
    'live_test_url': 'https://www.browseinfo.com/demo-request?app=bi_stock_block_quantity&version=16&edition=Community',
    "images":['static/description/Banner.gif'],
}
