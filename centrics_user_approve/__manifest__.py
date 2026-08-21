{
    'name': 'Centrics User Approve',
    'sequence': 1,
    'summary': "This module facilitate to approve or reject any records",
    "version": '15.0.0.1',
    'author': 'Centrics Business Solutions PVT Ltd',
    'company': 'Centrics Business Solutions PVT Ltd',
    'website': 'http://www.centrics.cloud/',
    'depends': ['base', 'stock'],
    'data': [
        'data/mail_template.xml',

        'wizard/request_user_approval_view.xml',
        'wizard/user_approve_or_reject_view.xml',

        # 'views/stock_picking_view.xml',
        'views/res_config_settings_view.xml',

        'security/ir.model.access.csv',
        'security/security.xml',
    ],
    'demo': [],
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
