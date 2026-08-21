{
    'name': 'Centrics Shipments',
    'sequence': 0,
    'version': '16.0.0.1',
    'license': 'LGPL-3',
    'summary': "Centrics Shipments",
    'description': """ This module contains the shipment details and the integration with purchase """,
    'author': 'Centrics Business Solutions PVT Ltd',
    'company': 'Centrics Business Solutions PVT Ltd',
    'website': 'http://www.centrics.cloud/',
    'depends': ['base', 'purchase'],
    'data': [
        'data/shipments_details_sequence.xml',
        'security/ir.model.access.csv',
        'security/centrics_shipments_security.xml',
        'views/shipments_details_view.xml',
    ],
    'demo': [
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
