# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Listview Freeze Header',
    'version': '1.0',
    'summary': 'The Listview Sticky Header module enhances the Odoo list view by making the header row sticky, ensuring it remains visible as users scroll through large datasets. This improves usability and makes it easier for users to reference column headers without losing context.',
    'description': """
        The Listview Sticky Header module enhances the Odoo list view by making the header row sticky, ensuring it remains visible as users scroll through large datasets. This improves usability and makes it easier for users to reference column headers without losing context.
                """,
    'category': 'Tools',
    'author': 'TechEmpyre',
    'depends': ['base'],
    'data': [
    ],
    'assets': {
        'web.assets_backend': [
            '/listview_fix_header/static/src/scss/listview.scss',
        ],
    },
    'demo': [],
    'images': [
        'static/description/main_screen.png'
    ],
    'price': 10,
    'currency': 'USD',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
}
