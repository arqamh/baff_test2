# -*- coding: utf-8 -*-

{
    'name': 'Baff Manufacturing Modifications',
    'version': '16.0.0',
    'category': 'mrp',
    'author': 'Centrics Business Solutions',
    'sequence': 0,
    'summary': 'This module contains all the MRP modifications according to their business nature.',
    'depends': ['base', 'mrp', 'mrp_account', 'analytic', 'mrp_workorder', 'mrp_workorder_hr', 'material_purchase_requisitions', 'odoo_job_costing_management', 'quality_control'],
    'data': [
        'data/data.xml',
        'data/mail_templates.xml',
        'security/mrp_security.xml',
        'security/ir.model.access.csv',
        'views/mrp_production_view.xml',
        'views/mrp_operations_view.xml',
        'views/mrp_workorder_view.xml',
        'views/quality_views.xml',
        'views/quality_alert_team_views.xml',
        'views/mrp_workcenter_view.xml',
        'wizard/request_user_approval_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'baff_manufacturing_modifications/static/src/xml/workorder_popup.xml',
            'baff_manufacturing_modifications/static/src/xml/working_employee_popup.xml',

            'baff_manufacturing_modifications/static/src/js/tablet.js',
            'baff_manufacturing_modifications/static/src/js/workorder_popup.js',
            'baff_manufacturing_modifications/static/src/js/working_employee_popup.js',

            'baff_manufacturing_modifications/static/src/css/workorder_popup.scss',
        ],
    },

    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}

