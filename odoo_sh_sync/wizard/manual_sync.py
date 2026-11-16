from odoo import models, fields


class OdooShSyncManualWizard(models.TransientModel):
    _name = 'odoo.sh.sync.manual_wizard'
    _description = 'Manual Odoo.sh Sync'

    config_id = fields.Many2one('odoo.sh.sync.config', required=True)
    
    def action_sync_now(self):
        self.ensure_one()
        try:
            result = self.env['odoo.sh.sync.engine'].execute_sync(self.config_id.id)
            log = self.env['odoo.sh.sync.log'].search(
                [('config_id', '=', self.config_id.id)],
                order='id desc',
                limit=1,
            )
            if not result:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Error',
                        'message': 'Sync failed before completion. Check Sync History for details.',
                        'type': 'danger',
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                }
            message = 'Sync completed'
            if log:
                message = (
                    f"Sync finished with status {log.status}. "
                    f"Total={log.total_records}, Success={log.success_records}, Errors={log.error_records}"
                )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': message,
                    'type': 'success',
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': str(e),
                    'type': 'danger',
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
