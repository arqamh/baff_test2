# -*- coding: utf-8 -*-
{
    'name': 'Baff Procurement Plan Job Tracking',
    'version': '16.0.1.0.0',
    'category': 'Purchases',
    'author': 'Centrics Business Solutions',
    'summary': 'Adds job/project reference, PO Created, GRN Done, and Pending qty '
               'columns to the Procurement Plan.',
    'description': """
Enhances procurement.plan with:
- Job Costing / Project references (sourced from MRP or linked requisition).
- PO Created quantity (aggregate of non-cancelled PO line qty).
- GRN Done quantity (qty_received aggregate).
- Balance quantity (required - received).
""",
    'depends': [
        'procurement_plan',
        'purchase',
        'odoo_job_costing_management',
        'baff_manufacturing_modifications',
        'material_purchase_requisitions',
    ],
    'data': [
        'views/procurement_plan_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
