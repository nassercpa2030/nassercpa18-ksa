{
    'name': 'Odoo.sh Sync - Local to Cloud',
    'version': '18.0.1.3.4',
    'category': 'Tools',
    'summary': 'Sync HR approvals between Odoo Online and Odoo.sh',
    'author': 'BeitBeirut Development Team',
    'depends': ['base', 'hr', 'approvals', 'sale', 'purchase', 'stock', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/sync_config_views.xml',
        'views/sync_log_views.xml',
        'views/manual_sync_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'images': [],
    'license': 'LGPL-3',
}
