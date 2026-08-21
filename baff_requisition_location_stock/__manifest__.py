# -*- coding: utf-8 -*-
{
    'name': 'Baff Material Request Location-wise Stock View',
    'version': '16.0.1.0.0',
    'category': 'Inventory',
    'author': 'Centrics Business Solutions',
    'summary': 'Mandatory source location with location-aware On-Hand / Forecasted stock on material requisition lines.',
    'description': """
- Makes Source Location (header) mandatory on material requisition confirmation.
- Propagates header location as the From Location on each line.
- Displays On-Hand and Forecasted quantity computed at the selected location.
""",
    'depends': [
        'material_purchase_requisitions',
    ],
    'data': [
        'views/requisition_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
