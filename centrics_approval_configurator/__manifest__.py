{
    'name': 'Approval Configurator',
    'version': '16.0.1.0.0',
    'summary': 'Define dynamic multi-level approval workflows for models',
    'category': 'Tools',
    'author': 'Centrics',
    'depends': ['base','mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/approval_config_views.xml'
    ],
    'installable': True,
    'application': True,
}
