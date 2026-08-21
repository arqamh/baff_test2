# -*- coding: utf-8 -*-
{
    'name': 'Baff WIP Material Dashboard',
    'version': '16.0.2.0.0',
    'category': 'Manufacturing',
    'author': 'Centrics Business Solutions',
    'summary': 'Real-time WIP material tracking dashboard for ongoing Manufacturing Orders.',
    'description': """
Material ongoing / WIP report dashboard.

Ongoing MO states tracked: confirmed, progress, to_close.

Tabs:
- Summary Overview: MO-level WIP totals.
- Material Breakdown: per-component qty + availability + procurement.
- Procurement Status: grouped by request/PO/receipt state.
- Stock Gaps & Suggestions: insufficient components only.
- Actual Material Issued: consumed materials per BOM.
- Variant Material: components from multi-variant templates.
""",
    'depends': [
        'mrp',
        'stock',
        'stock_account',
        'purchase',
        'baff_manufacturing_modifications',
        'material_purchase_requisitions',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/wip_material_line_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
