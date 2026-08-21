{
    'name': 'Procurement Plan',
    'sequence': 0,
    'version': '16.0.0.1',
    'license': 'LGPL-3',
    'summary': "Procurement Plan ",
    'author': 'Centrics Business Solutions PVT Ltd',
    'company': 'Centrics Business Solutions PVT Ltd',
    'website': 'http://www.centrics.cloud/',
    'depends': ['base', 'stock','purchase', 'mrp'],
    'data': [
        'security/security.xml',
        'security/record_rule.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/data.xml',

        'views/procurement_plan_views.xml',
        'views/res_config_settings_views.xml',
        'views/purchase_order.xml',
        'views/mrp_view.xml',

        'wizard/merge_procurement_plan_wizard.xml',
    ],
    'demo': [
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
