# -*- coding: utf-8 -*-
{
    'name': 'Product Category Change Restriction',
    'version': '16.0.1.0.0',
    'sequence': 1,
    'category': 'Inventory',
    'license': 'OPL-1',
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'http://www.centrics.cloud/',
    'summary': 'Restrict product category changes to authorized users only',
    'description': """
        This module allows administrators to control who can change product categories.

        Key Features:

        * Enable/disable category change restriction per company
        * Dedicated security group for authorized users
        * Field becomes read-only for unauthorized users
        * Validation at code level prevents unauthorized changes
        * Clear error messages for users without permission

        Configuration:

        1. Go to Settings → Inventory
        2. Enable "Restrict Product Category Change"
        3. Assign "Change Product Category" permission to authorized users
    """,
    'depends': ['stock', 'product'],
    'data': [
        'security/security.xml',
        'views/res_config_settings_views.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
