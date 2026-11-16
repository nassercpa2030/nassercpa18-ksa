from odoo import fields, models


class OdooShSyncMap(models.Model):
    _name = 'odoo.sh.sync.map'
    _description = 'Odoo.sh Sync ID Map'
    _rec_name = 'display_name'
    _order = 'model_name, local_res_id'

    config_id = fields.Many2one(
        'odoo.sh.sync.config',
        string='Sync Configuration',
        required=True,
        ondelete='cascade',
        index=True,
    )
    model_name = fields.Char(required=True, index=True)
    local_res_id = fields.Integer(required=True, index=True)
    remote_res_id = fields.Integer(required=True, index=True)
    last_write_date = fields.Datetime()
    display_name = fields.Char(compute='_compute_display_name', store=True)

    _sql_constraints = [
        (
            'config_model_local_unique',
            'unique(config_id, model_name, local_res_id)',
            'A local record can only have one remote mapping per sync configuration.',
        ),
    ]

    def _compute_display_name(self):
        for record in self:
            record.display_name = (
                f"{record.model_name} {record.local_res_id} -> {record.remote_res_id}"
            )
