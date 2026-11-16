from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class OdooShSyncConfig(models.Model):
    _name = 'odoo.sh.sync.config'
    _description = 'Odoo.sh Sync Configuration'

    name = fields.Char('Configuration Name', required=True)
    active = fields.Boolean('Active', default=True)
    
    # Odoo.sh Connection
    odoo_sh_url = fields.Char('Online Source URL', required=True)
    odoo_sh_database = fields.Char('Online Source Database', required=True)
    odoo_sh_username = fields.Char('Online Source Username', required=True)
    odoo_sh_password = fields.Char('Online Source Password', required=True)
    
    # Local Companies
    local_company_ids = fields.Many2many('res.company', string='Companies to Sync')
    unknown_local_user_ids = fields.Many2many(
        'res.users',
        'odoo_sh_sync_config_unknown_user_rel',
        'config_id',
        'user_id',
        string='Users To Sync As Unknown',
    )
    user_mapping_ids = fields.One2many(
        'odoo.sh.sync.user.map',
        'config_id',
        string='User Mapping Rules',
    )
    
    # Sync direction: this installation is Odoo.sh; Online is the source.
    sync_direction = fields.Selection(
        [
            ('sh_to_online', 'Odoo.sh → Online'),
            ('online_to_sh', 'Online → Odoo.sh'),
        ],
        string='Sync Direction',
        required=True,
        default='online_to_sh',
    )
    inbound_models = fields.Text(
        'Online Models to Import',
        default=(
            'hr.department\n'
            'hr.job\n'
            'hr.employee\n'
            'approval.request\n'
            'approval.approver'
        ),
        help='Imports HR employees and actual employee-created approval requests/approvers from Online. Approval categories are matched by name as references and are not imported.',
    )

    # Sync Config
    sync_models = fields.Text(
        'Models to Sync',
        default=(
            'res.company\n'
            'res.partner\n'
            'product.category\n'
            'product.template\n'
            'product.product\n'
            'sale.order\n'
            'sale.order.line\n'
            'purchase.order\n'
            'purchase.order.line\n'
            'stock.picking\n'
            'stock.move\n'
            'stock.move.line\n'
            'account.move\n'
            'account.move.line\n'
            'account.payment\n'
            'pos.order\n'
            'pos.order.line\n'
            'pos.payment'
        ),
    )
    sync_time = fields.Float('Sync Time (Hour)', default=0.0)
    last_sync_date = fields.Datetime('Last Sync', readonly=True)
    inbound_last_sync_date = fields.Datetime('Last Online Import', readonly=True)
    merge_duplicates = fields.Boolean('Merge Duplicates', default=True)
    sync_batch_size = fields.Integer('Batch Size', default=100)
    sync_responsible_users = fields.Boolean('Sync Responsible Users', default=True)
    fallback_remote_user_login = fields.Char('Fallback Remote User Login', default='unknown')
    fallback_remote_user_name = fields.Char('Fallback Remote User Name', default='Unknown')

    def test_connection(self):
        self.ensure_one()
        try:
            from xmlrpc import client

            url = self.odoo_sh_url.rstrip('/')
            common = client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
            common.version()
            uid = common.authenticate(self.odoo_sh_database, self.odoo_sh_username, self.odoo_sh_password, {})
            if not uid:
                raise ValueError("Authentication failed. Check database, username, and password.")

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Connection OK!',
                    'type': 'success',
                },
            }
        except Exception as e:
            _logger.exception("Odoo.sh connection test failed")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': str(e),
                    'type': 'danger',
                },
            }
