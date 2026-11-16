from odoo import models, fields
from datetime import datetime


class OdooShSyncLog(models.Model):
    _name = 'odoo.sh.sync.log'
    _description = 'Odoo.sh Sync Log'
    _order = 'create_date DESC'

    name = fields.Char('Sync Name', readonly=True)
    config_id = fields.Many2one('odoo.sh.sync.config', readonly=True)
    sync_start = fields.Datetime('Start', readonly=True)
    sync_end = fields.Datetime('End', readonly=True)
    duration = fields.Float('Duration (s)', readonly=True, compute='_compute_duration')
    status = fields.Selection([('pending', 'Pending'), ('success', 'Success'), ('error', 'Error'), ('partial', 'Partial')], readonly=True, default='pending')
    total_records = fields.Integer('Total', readonly=True)
    success_records = fields.Integer('Success', readonly=True)
    error_records = fields.Integer('Errors', readonly=True)
    sync_details = fields.Text('Details', readonly=True)
    error_log = fields.Text('Error Log', readonly=True)

    def _compute_duration(self):
        for log in self:
            if log.sync_start and log.sync_end:
                log.duration = (log.sync_end - log.sync_start).total_seconds()
            else:
                log.duration = 0
