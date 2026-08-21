{
    'name': 'Centrics Purchase Multi User Approval',
    'sequence': 0,
    'version': '16.0.0.1',
    'license': 'LGPL-3',
    'summary': "This module contains multi user approval for purchase orders",
    'author': 'Centrics Business Solutions PVT Ltd',
    'company': 'Centrics Business Solutions PVT Ltd',
    'website': 'http://www.centrics.cloud/',
    'depends': ['base', 'purchase', 'purchase_stock'],
    'data': [
        'data/mail_template.xml',
        'security/ir.model.access.csv',
        'security/security_groups.xml',
        'views/res_company.xml',
        'views/purchase_order.xml',
        'wizards/purchase_order_approvers_wizard.xml',
    ],
    'demo': [
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
