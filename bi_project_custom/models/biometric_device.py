from odoo import models, fields

class BiometricDevice(models.Model):
    _name = "biometric.device"
    _description = "Biometric Device"

    name = fields.Char(
        string="Device Name",
        required=True
    )

    ip = fields.Char(
        string="IP Address",
        required=True
    )

    port = fields.Integer(
        default=4370
    )

    password = fields.Char()

    active = fields.Boolean(
        default=True
    )

    last_sync = fields.Datetime()

    mode = fields.Selection([
        ('tcp', 'TCP/IP'),
        ('adms', 'ADMS')
    ], default='tcp')

    adms_url = fields.Char(
        string="ADMS URL"
    )
