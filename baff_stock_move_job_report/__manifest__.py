# -*- coding: utf-8 -*-
{
    'name': 'Baff Stock Move Job Report',
    'version': '16.0.1.0.0',
    'category': 'Inventory',
    'author': 'Centrics Business Solutions',
    'summary': 'Dedicated Stock Move report searchable and printable by Project / Job.',
    'description': """
Adds a Stock Moves by Project/Job report with:
- Search filters for Project / Job Name, Job Number, Product, Date range, Source/Destination Location.
- Printable QWeb PDF for the filtered list.
- Stored computed Job Costing, Project and Job Number fields on stock.move.
""",
    'depends': [
        'stock',
        'mrp',
        'odoo_job_costing_management',
        'baff_manufacturing_modifications',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_move_views.xml',
        'report/stock_move_job_report.xml',
        'report/stock_move_job_templates.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
