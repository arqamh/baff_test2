# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright 2019 EquickERP
#
##############################################################################
{
    'name': "Cancel Stock Picking/Inventory Adjustment",
    'category': 'Warehouse',
    'version': '16.0.1.0.0',
    'sequence': 1,
    'description': """
        This Module allows user to cancel done stock move.
        * Allow user to cancel done stock move.
        * Allow user to Reset back to Draft cancelled stock move / picking.
        * User can cancel Inventory Adjustments which is already validated.
        * User can cancel done Scrap Order.
        * When user cancel Incoming/Outgoing shipment it also update Sales/Purchase orders Delivered/Received Quantity.
        * While user cancel Stock transaction it also cancel the related Account Entries.
    """,
    'summary': """cancel stock move cancel sale order cancel delivery order cancel picking reverse picking reset picking cancel receipt cancel incoming shipment cancel adjustment cancel inventory adjustment cancel scrap order STOCK PICKING CANCEL cancel po|cancel so""",
    'depends': ['stock_account'],
    'license': 'OPL-1',
    'website': "",
    'data': [
        'security/security_groups.xml',
        'views/stock_picking_views.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
