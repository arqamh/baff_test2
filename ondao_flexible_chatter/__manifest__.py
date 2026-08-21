# Copyright 2024 Ondao IT
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    'name': 'Flexible Chatter',
    'category': 'Extra Tools',
    "summary": "Add an option to change the chatter position",
    'description': """
Flexible Chatter allows to control the width of the chatter manually or change its location.
    """,
    "version": "16.0.0.0",
    "author": "Deniss Matjusevs (Ondao)",
    'license': 'OPL-1',
    'depends': ['web', 'mail'],
    "data": [
        "views/res_users.xml",
        "views/web.xml"
    ],
    'assets': {
        'web.assets_backend': [
            'ondao_flexible_chatter/static/src/js/views/**/*'
        ]
    },
    'images': ['static/description/chatter.gif'],
    'support': 'deniss.matjusevs@gmail.com',
    "price": "35.00",
    "currency": "EUR",
}
