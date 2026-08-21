# -*- coding: utf-8 -*-
{
    'name': 'Restrict Create and Edit',
    'sequence': 10,
    'version': '16.0.1.0.0',
    'summary': "Hide 'Create' and 'Create and Edit' options on selected Many2one fields",
    'description': """
Restrict Create and Edit on Many2one fields
===========================================

Adds a configuration menu under Settings > Technical > Restrict Create and Edit.
Admins pick a model, pick one or more of its Many2one fields, and the web client
hides the 'Create' and 'Create and Edit' options on those fields' dropdowns.

Users can still select existing records; new records must be created from the
proper master-data menus.
    """,
    'author': 'Centrics Business Solutions PVT Ltd',
    'company': 'Centrics Business Solutions PVT Ltd',
    'website': 'http://www.centrics.cloud/',
    'category': 'Technical',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/restrict_create_and_edit_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'centrics_restrict_create_and_edit/static/src/js/many2one_restrict.js',
        ],
        'web.assets_tests': [
            'centrics_restrict_create_and_edit/static/tests/tours/test_restrict_m2o_tour.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
