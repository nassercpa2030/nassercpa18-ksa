from odoo import api, fields, models, _


class UserEmailCredentials(models.Model):
    _name = 'user.email.credentials'
    _description = 'User Email Credentials'
    _rec_name = 'server'

    server = fields.Char(string="Server")
    port = fields.Integer(string="Port")
    is_ssl = fields.Boolean(string="SSL/TLS")
    user = fields.Char(string="User")
    password = fields.Char(string="Password")
    user_id = fields.Many2one('res.users', string="User ID", default=lambda self: self.env.user)
    user_smtp_status = fields.Selection([
        ('disconnected', 'Not Connected'),
        ('connected', 'Connected'),
    ], string="Connection Status", default='disconnected', readonly=True)
    server_type = fields.Selection([('incoming', 'Incoming'), ('outgoing', 'Outgoing')], default='incoming', string="Server Type")


    @api.model
    def create(self, vals):
        record = super().create(vals)
        if not self.env.context.get('skip_sync'):
            record._sync_to_res_users()
        return record

    def write(self, vals):
        for rec in self:
            # store previous user_id
            old_user = rec.user_id
            res = super(UserEmailCredentials, rec).write(vals)
            # Handle old user if user_id changed
            if 'user_id' in vals:
                old_user.sudo().with_context(skip_sync=True).write({
                    'server': False,
                    'port': False,
                    'is_ssl': False,
                    'mail_user': False,
                    'mail_password': False,
                })

            # Sync current user's info
            rec._sync_to_res_users()

        return res

    def _sync_to_res_users(self):
        """Sync current credentials to related res.users record"""
        for rec in self:
            if rec.user_id:
                rec.user_id.sudo().with_context(skip_sync=True).write({
                    'server': rec.server,
                    'port': rec.port,
                    'is_ssl': rec.is_ssl,
                    'mail_user': rec.user,
                    'mail_password': rec.password,
                    'user_smtp_status': rec.user_smtp_status,
                })

    def unlink(self):
        """Clear related res.users fields when deleting credentials"""
        for rec in self:
            if rec.user_id:
                rec.user_id.with_context(skip_sync=True).write({
                    'server': False,
                    'port': False,
                    'is_ssl': False,
                    'mail_user': False,
                    'mail_password': False,
                })
        return super().unlink()


    def action_clear_smtp_values(self):
        self.ensure_one()

        if self.user_id:
            self.user_id.sudo().with_context(skip_sync=True).write({
                'server': False,
                'port': False,
                'is_ssl': False,
                'mail_user': False,
                'mail_password': False,
                'user_smtp_status': 'disconnected',
            })

        self.sudo().with_context(skip_sync=True).write({
            'server': False,
            'port': False,
            'is_ssl': False,
            'user': False,
            'password': False,
            'user_smtp_status': 'disconnected',
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cleared'),
                'message': _('SMTP credentials have been erased successfully.'),
                'type': 'warning',
                'sticky': True,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            }
        }


    def test_mail_server_connection(self):
        self.ensure_one()
        server_values = {
            'name': 'Temporary IMAP Server',
            'server_type': 'imap',
            'server': self.server,
            'port': self.port,
            'user': self.user,
            'password': self.password,
            'is_ssl': self.is_ssl,
        }

        server_obj = self.env['fetchmail.server'].new(server_values)

        try:
            connection = server_obj.connect()
            connection.noop()
            connection.logout()
        except Exception as e:
            self.sudo().user_smtp_status = 'disconnected'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Failed'),
                    'message': _('SMTP Connection failed: %s') % str(e),
                    'delay': 3000,
                    'type': 'danger',
                    'sticky': True,
                    'next': {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    }
                }
            }
        else:
            self.sudo().user_smtp_status = 'connected'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('SMTP Connection successful!'),
                    'delay': 3000,
                    'type': 'success',
                    'sticky': True,
                    'next': {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    }
                }
            }
