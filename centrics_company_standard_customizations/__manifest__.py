{
    'name': 'Company Profile Standard Customization',
    'version': '16.0.1.0.0',
    'sequence': 1,
    'category': 'Hidden',
    'license': 'OPL-1',
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'http://www.centrics.cloud/',
    'summary': 'Res Company Customizations',
    'description': """
        1. Added Company Code
   """,
    'depends': [
        'base',
    ],
    'data': [

       'views/res_company_views.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
