from odoo import fields, models


class OdooShSyncUserMap(models.Model):
    _name = 'odoo.sh.sync.user.map'
    _description = 'Odoo.sh Sync User Mapping'
    _order = 'config_id, local_user_id'

    config_id = fields.Many2one(
        'odoo.sh.sync.config',
        string='Sync Configuration',
        required=True,
        ondelete='cascade',
        index=True,
    )
    local_user_id = fields.Many2one(
        'res.users',
        string='Local User',
        required=True,
        index=True,
    )
    mapping_type = fields.Selection(
        [
            ('match', 'Match Same User'),
            ('fallback', 'Use Fallback User'),
            ('remote', 'Use Specific Remote User'),
        ],
        string='Mapping Rule',
        required=True,
        default='match',
    )
    remote_user_login = fields.Char('Remote User Login')
    remote_user_name = fields.Char('Remote User Name')
    note = fields.Char('Note')

    _sql_constraints = [
        (
            'config_local_user_unique',
            'unique(config_id, local_user_id)',
            'Each local user can only have one sync mapping per configuration.',
        ),
    ]
