# -*- coding: utf-8 -*-
{
    'name': 'Baff Inventory As on Date',
    'version': '16.0.1.0.0',
    'category': 'Inventory',
    'author': 'Centrics Business Solutions',
    'summary': 'User-friendly Inventory As on Date report with Location / Product / Date filters.',
    'description': """
Adds a wizard-driven Inventory As on Date report that:
- Requires an As-on Date.
- Accepts optional Location, Product and Product Category filters.
- Renders results as a list and pivot of (Product x Location -> Quantity).
""",
    'depends': [
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/inventory_as_on_date_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
