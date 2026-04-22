# -*- coding: utf-8 -*-
{
    'name': "Message to partner via whats-app",

    'summary': """
        This module allow user to send message to partner via whats-app.
    """,

    'description': """
        In this module you will get whats-app link to partner view. This module allow user to send message to partner via whats-app.
    """,

    'author': "MP Technolabs",
    'website': "https://mptechnolabs.com/",
    'category': 'Sales',
    'version': '1.0',
    'license': 'AGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['sale'],
    'demo': [
    ],
    # always loaded
    'data': [
        'views/whatsapp_partner_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
#     'price': 00.00,
#     'currency': 'EUR',
#     'images': [
#         'static/description/v1-banner.png',
#         'static/description/v2-banner.png' 
#         
#     ],

}