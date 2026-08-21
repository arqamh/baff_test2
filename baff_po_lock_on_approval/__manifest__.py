# -*- coding: utf-8 -*-
{
    'name': 'Baff PO Lock on Approval',
    'version': '16.0.1.0.0',
    'category': 'Purchases',
    'author': 'Centrics Business Solutions',
    'summary': 'Locks Product, Quantity and UoM on approved POs and on vendor bills derived from them.',
    'description': """
Once a Purchase Order is approved (state = purchase or done), the following
fields become read-only and are enforced server-side:
- Product
- Quantity
- Unit of Measure

This applies both on the PO itself and on the vendor bill lines linked to an
approved PO (via purchase_line_id).
""",
    'depends': [
        'purchase',
        'account',
    ],
    'data': [
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
