from odoo import api, fields, models, _

class ResUsers(models.Model):
    _inherit = "res.users"

    server = fields.Char(string="Server")
    port = fields.Integer(string="Port")
    is_ssl = fields.Boolean(string="SSL/TLS")
    mail_user = fields.Char(string="User")
    mail_password = fields.Char(string="Password")
    user_smtp_status = fields.Selection([
        ('disconnected', 'Not Connected'),
        ('connected', 'Connected'),
    ], string="Connection Status", default='disconnected', readonly=True)
    copilot_agent_ids = fields.Many2many('copilot.agent.dashboard', string='Copilot Agents')

    # store manually added agents
    previous_agent_group_ids = fields.Many2many(
        'ai.agent.group',
        'odoo_ai_agent_previous_agent_group_rel',
        string='Manual Copilot Agents'
    )

    @api.onchange('agent_group_ids')
    def _onchange_agent_group_ids(self):
        for record in self:
            prev = record.previous_agent_group_ids
            curr = record.agent_group_ids

            if prev or curr:
                removed = prev - curr
                added = curr - prev
                common = prev & curr
                common = self.env['ai.agent.group'].browse(common.ids)

                # REMOVE agents safely
                if removed:
                    agents_to_remove = self.env['copilot.agent.dashboard'].search([
                        ('ai_agent_group_ids', 'in', removed.ids)
                    ])

                    # Keep agents that still belong to any remaining group
                    agents_to_remove = agents_to_remove.filtered(
                        lambda a: not (a.ai_agent_group_ids & curr)
                    )
                    not_needed_to_remove = []
                    for rv_agent in agents_to_remove:
                        if rv_agent.ai_agent_group_ids & common:
                            not_needed_to_remove.extend(rv_agent.ids)
                    agents_to_remove = agents_to_remove.filtered( lambda a: a.id not in not_needed_to_remove )
                    record.copilot_agent_ids = [(3, agent.id) for agent in agents_to_remove]
                    # record.copilot_agent_ids = self.env['copilot.agent.dashboard'].search([
                    #     ('id', 'in', record.copilot_agent_ids.ids),('id', 'not in', agents_to_remove.ids)
                    # ])

                # ADD agents
                if added:
                    agents_to_add = self.env['copilot.agent.dashboard'].search([
                        ('ai_agent_group_ids', 'in', added.ids)
                    ])
                    record.copilot_agent_ids = [(4, a.id) for a in agents_to_add]
                    # record.copilot_agent_ids |= agents_to_add

            # Initial load
            if not prev and curr:

                agents = self.env['copilot.agent.dashboard'].search([
                    ('ai_agent_group_ids', 'in', curr.ids)
                ])
                # record.copilot_agent_ids |= agents
                record.copilot_agent_ids = [(4, a.id) for a in agents]

            # Store current groups
            record.previous_agent_group_ids = curr


    @property
    def SELF_WRITEABLE_FIELDS(self):
        # get base fields
        base_fields = super(ResUsers, self).SELF_WRITEABLE_FIELDS
        # add your custom fields
        return base_fields + ['server', 'port', 'is_ssl', 'mail_user', 'mail_password', 'user_smtp_status']

    def write(self, vals):
        res = super().write(vals)
        # res = super(ResUsers, self.sudo()).write(vals)

        if not self.env.context.get('skip_sync'):
            # Only sync if email credential fields are being changed
            email_fields = {'server', 'port', 'is_ssl', 'mail_user', 'mail_password', 'user_smtp_status'}
            if any(field in vals for field in email_fields):
                for rec in self:
                    cred = self.env['user.email.credentials'].search([('user_id', '=', rec.id)], limit=1)
                    if cred:
                        cred.with_context(skip_sync=True).write({
                            'server': vals.get('server', rec.server),
                            'port': vals.get('port', rec.port),
                            'is_ssl': vals.get('is_ssl', rec.is_ssl),
                            'user': vals.get('mail_user', rec.mail_user),
                            'password': vals.get('mail_password', rec.mail_password),
                            'user_smtp_status': vals.get('user_smtp_status', rec.user_smtp_status),
                        })
                    else:
                        # Auto-create only if actual email fields are present
                        self.env['user.email.credentials'].with_context(skip_sync=True).create({
                            'user_id': rec.id,
                            'server': vals.get('server', rec.server),
                            'port': vals.get('port', rec.port),
                            'is_ssl': vals.get('is_ssl', rec.is_ssl),
                            'user': vals.get('mail_user', rec.mail_user),
                            'password': vals.get('mail_password', rec.mail_password),
                            'user_smtp_status': vals.get('user_smtp_status', rec.user_smtp_status),
                        })
        return res

    def action_clear_smtp_values(self):
        self.ensure_one()

        self.sudo().with_context(skip_sync=True).write({
            'server': False,
            'port': False,
            'is_ssl': False,
            'mail_user': False,
            'mail_password': False,
            'user_smtp_status': 'disconnected',
        })

        cred = self.env['user.email.credentials'].search(
            [('user_id', '=', self.id)],
            limit=1
        )
        if cred:
            cred.sudo().with_context(skip_sync=True).write({
                'server': False,
                'port': False,
                'user': False,
                'password': False,
                'is_ssl': False,
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
            'user': self.mail_user,
            'password': self.mail_password,
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
