{
    'name': 'Baff CRM Modifications',
    'sequence': 0,
    'version': '16.0.0.1',
    'license': 'LGPL-3',
    'summary': "Baff CRM Modifications",
    'description': """ This module contains all the CRM modifications of the Baff""",
    'author': 'Centrics Business Solutions PVT Ltd',
    'company': 'Centrics Business Solutions PVT Ltd',
    'website': 'http://www.centrics.cloud/',
    'depends': ['base', 'crm', 'sale', 'sale_crm'],
    'data': [
        'data/sequence.xml',
        'views/crm_lead_view.xml',
        'views/crm_inquiry_view.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
