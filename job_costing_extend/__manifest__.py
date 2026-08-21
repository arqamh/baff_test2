{
    'name': 'Job Costing Extend',
    'version': '1.0',
    'sequence': 10,
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'http://www.centrics.cloud/',
    'summary': 'This module is a Extend job costing',
    'description': """This module is a Extend job costing""",
    'installable': True,
    'application': True,
    'auto_install': False,
    'depends': [
        'odoo_job_costing_management',
        'material_purchase_requisitions',
        'centrics_material_purchase_req_analytic',
     ],
    'data': [
        'views/stock_picking_type_views.xml',
        'views/material_purchase_requisitions.xml',
    ]

}
