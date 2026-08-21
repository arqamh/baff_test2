# -*- coding: utf-8 -*-

{
    "name": "Material Purchase Requisition Analytics",
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'http://www.centrics.cloud/',
    "support": "sales@centrics.cloud",
    "category": "Point of Sale",
    "summary": "Interpay SoftPos windows connector for Odoo POS",
    "description": "Interpay SoftPos windows connector for Odoo POS",
    "version": "16.0.1.0.0",
    "depends": [
        'stock',
        'analytic',
        'material_purchase_requisitions',
        'procurement_plan'
    ],
    "data": [
        "views/procuremnt_plan_views.xml",
        "views/material_purchase_requisition_views.xml",
        "views/stock_picking_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "application": False,
    "auto_install": False,
    "installable": True,
    "license": 'LGPL-3'
}
