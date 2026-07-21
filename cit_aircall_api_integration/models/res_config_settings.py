# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

import pytz
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.cit_aircall_api_integration.models.authorization import AuthorizeAircallApi


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    aircall_auth = fields.Boolean(
        config_parameter='cit_aircall_api_integration.default_aircall_auth')
    phone_formate = fields.Boolean(
        config_parameter='cit_aircall_api_integration.default_phone_formate')
    timezone_setting = fields.Selection(
        selection=lambda self: [(tz, tz) for tz in pytz.all_timezones],
        string='Timezone',
        config_parameter='cit_aircall_api_integration.timezone_setting')
    api_url = fields.Char(
        string='Aircall API URL', default='https://api.aircall.io',
        config_parameter='cit_aircall_api_integration.default_api_url',
        help='This is the URL used for API integration with Aircall.')
    api_id = fields.Char(
        string='Aircall API Key - ID', default='dummy',
        config_parameter='cit_aircall_api_integration.default_api_id',
        help='This is the API ID used for authentication in Aircall API integration.')
    api_token = fields.Char(
        string='Aircall API Key - Secret', default='dummy',
        config_parameter='cit_aircall_api_integration.default_api_token',
        help='Enter your API token here. '
             'This token is used for integration with Aircall.')
    aircall_integration_token = fields.Char(
        string='Aircall Webhook Token', default='dummy',
        config_parameter='cit_aircall_api_integration.default_aircall_integration_token',
        help='Enter your Aircall integration token here. '
             'This token is used for integration purposes.')
    number_config_ids = fields.Many2many(
        'number.number', string='Connected Numbers',
        related='company_id.number_config_ids', readonly=False)
    number_crm_config_ids = fields.Many2many(
        'number.number', relation='config_crm_rel', column1='config_id',
        column2='crm_id', string='CRM Config')
    number_helpdesk_config_ids = fields.Many2many(
        'number.number', relation='config_helpdesk_rel', column1='config_id',
        column2='helpdesk_id', string='Helpdesk Config')
    allow_create_unknown_contacts = fields.Boolean(
        string='Allow Odoo Contact Creation For Unknown Number',
        config_parameter='cit_aircall_api_integration.allow_create_unknown_contacts')
    manual_call_loging = fields.Boolean(
        string='Manual Call Logging For Duplicates',
        config_parameter='cit_aircall_api_integration.manual_call_loging')
    enable_crm_module = fields.Boolean(
        string='Enable Crm Module',
        config_parameter='cit_aircall_api_integration.enable_crm_module')
    enable_helpdesk_module = fields.Boolean(
        string='Enable Helpdesk Module',
        config_parameter='cit_aircall_api_integration.enable_helpdesk_module')
    helpdesk_log_note_setting = fields.Selection(
        selection=[
            ('open_new_ticket', 'Create a new ticket'),
            ('add_log_note_exciting', 'Log call note in existing ticket')
        ], string='Helpdesk Log Note Setting : ',
        config_parameter='cit_aircall_api_integration.helpdesk_log_note_setting')
    enable_summary = fields.Boolean(
        string='Enable Summary',
        config_parameter='cit_aircall_api_integration.enable_summary_feature')
    enable_transcription = fields.Boolean(
        string='Enable Transcription',
        config_parameter='cit_aircall_api_integration.enable_transcription_feature')
    enable_sms = fields.Boolean(
        string='Enable SMS', config_parameter='cit_aircall_api_integration.enable_sms')
    enable_sms_in_chatter = fields.Boolean(
        string='Log SMS under Activities?',
        config_parameter='cit_aircall_api_integration.enable_sms_in_chatter')
    enable_try_again_syncing = fields.Boolean(
        string='Manually try again to sync the fail contact?',
        config_parameter='cit_aircall_api_integration.enable_try_again_syncing')

    @api.onchange('enable_crm_module')
    def _onchange_enable_crm_module(self):
        """ Triggered when CRM module toggle changes."""
        if self.enable_crm_module:
            crm_module = self.env['ir.module.module'].sudo().search([
                ('name', '=', 'crm')
            ], limit=1)
            if not crm_module or crm_module.state != 'installed':
                raise UserError(
                    _('CRM module is not installed. Please install the CRM module.'))
            self._create_dynamic_field()
            self._create_dynamic_views()
            self._create_dynamic_action()

    @api.onchange('enable_helpdesk_module')
    def _onchange_enable_helpdesk_module(self):
        """Triggered when CRM module toggle changes."""
        if self.enable_helpdesk_module:
            helpdesk_module = self.env['ir.module.module'].sudo().search([
                ('name', '=', 'helpdesk')
            ], limit=1)
            if not helpdesk_module or helpdesk_module.state != 'installed':
                raise UserError(_(
                    'Helpdesk module is not installed. '
                    'Please install the Helpdesk module.'))
            self._create_dynamic_helpdesk_field()
            self._create_dynamic_helpdesk_views()
            self._create_dynamic_helpdesk_action()

    def _create_dynamic_field(self):
        """Adds 'x_add_log_note' field to crm lead if it doesn't exist."""
        model = self.env['ir.model'].search([
            ('model', '=', 'crm.lead')
        ], limit=1)
        if not model:
            return

        if not self.env['ir.model.fields'].search_count([
            ('model_id', '=', model.id),
            ('name', '=', 'x_add_log_note')
        ]):
            self.env['ir.model.fields'].create({
                'name': 'x_add_log_note',
                'field_description': 'Add Log Note',
                'model_id': model.id,
                'ttype': 'boolean',
                'state': 'manual',
            })

    def _create_dynamic_helpdesk_field(self):
        """Adds 'x_add_log_note' and 'x_partner_mobile' fields to helpdesk ticket
        if they don't exist."""
        model = self.env['ir.model'].search([('model', '=', 'helpdesk.ticket')], limit=1)
        if not model:
            return

        field_data = [
            ('x_add_log_note', 'Add Log Note', 'boolean'),
            ('x_partner_mobile', 'Partner Mobile', 'char'),
        ]

        for field_name, field_description, field_type in field_data:
            if not self.env['ir.model.fields'].search_count([
                ('model_id', '=', model.id),
                ('name', '=', field_name)
            ]):
                self.env['ir.model.fields'].create({
                    'name': field_name,
                    'field_description': field_description,
                    'model_id': model.id,
                    'ttype': field_type,
                    'state': 'manual',
                })

    @api.model
    def _create_dynamic_views(self):
        """Creates form and list views for crm lead."""
        tree_view = self.env.ref(
            'crm.crm_case_tree_view_oppor', raise_if_not_found=False)
        form_view = self.env.ref(
            'crm.crm_lead_view_form', raise_if_not_found=False)

        if tree_view and not self.env['ir.ui.view'].search_count([
            ('name', '=', 'view.crm.tree.inh.x_add_log_note')
        ]):
            self.env['ir.ui.view'].create({
                'name': 'view.crm.tree.inh.x_add_log_note',
                'model': 'crm.lead',
                'inherit_id': tree_view.id,
                'arch': """
                    <xpath expr="//button[@name='action_snooze']" position="after">
                        <field name="x_add_log_note" widget="boolean_toggle"/>
                    </xpath>
                """
            })

        if form_view and not self.env['ir.ui.view'].search_count([
            ('name', '=', 'view.crm.form.inh.x_add_log_note')
        ]):
            self.env['ir.ui.view'].create({
                'name': 'view.crm.form.inh.x_add_log_note',
                'model': 'crm.lead',
                'inherit_id': form_view.id,
                'arch': """
                    <xpath expr="//field[@name='tag_ids']" position="after">
                        <field name="x_add_log_note" widget="boolean_toggle"/>
                    </xpath>
                """
            })

    @api.model
    def _create_dynamic_action(self):
        """Create the 'Opportunities' action dynamically."""
        action = self.env['ir.actions.act_window'].search([
            ('name', '=', 'aircall_crm_Opportunities')
        ], limit=1)
        if not action:
            self.env['ir.actions.act_window'].create({
                'name': 'aircall_crm_Opportunities',
                'res_model': 'crm.lead',
                'view_mode': 'kanban,list,graph,pivot,form,calendar,activity',
                'domain': [('type', '=', 'opportunity')],
                'search_view_id': self.env.ref(
                    'crm.view_crm_case_opportunities_filter').id,
            })

        return action

    @api.model
    def _create_dynamic_helpdesk_action(self):
        """ Create the 'Helpdesk Tickets' action dynamically if not found """
        action = self.env['ir.actions.act_window'].search([
            ('name', '=', 'Tickets'),
            ('res_model', '=', 'helpdesk.ticket')
        ], limit=1)

        if not action:
            action = self.env['ir.actions.act_window'].create({
                'name': 'Tickets',
                'res_model': 'helpdesk.ticket',
                'view_mode': 'list,kanban,form,activity,pivot,graph,cohort',
                'search_view_id': self.env.ref(
                    'helpdesk.helpdesk_tickets_view_search').id,
            })

        return action

    @api.model
    def _create_dynamic_helpdesk_views(self):
        """Creates form and list views for crm lead."""
        tree_view = self.env.ref(
            'helpdesk.helpdesk_tickets_view_tree', raise_if_not_found=False)
        form_view = self.env.ref(
            'helpdesk.helpdesk_ticket_view_form', raise_if_not_found=False)

        if tree_view and not self.env['ir.ui.view'].search_count([
            ('name', '=', 'view.helpdesk.tree.inh.x_add_log_note')
        ]):
            self.env['ir.ui.view'].create({
                'name': 'view.helpdesk.tree.inh.x_add_log_note',
                'model': 'helpdesk.ticket',
                'inherit_id': tree_view.id,
                'arch': """
                    <xpath expr="//field[@name='stage_id']" position="after">
                        <field name="x_add_log_note" widget="boolean_toggle"/>
                    </xpath>
                """
            })

        if form_view and not self.env['ir.ui.view'].search_count([
            ('name', '=', 'view.helpdesk.form.inh.x_add_log_note')
        ]):
            self.env['ir.ui.view'].create({
                'name': 'view.helpdesk.form.inh.x_add_log_note',
                'model': 'helpdesk.ticket',
                'inherit_id': form_view.id,
                'arch': """
                    <xpath expr="//field[@name='email_cc']" position="after">
                        <field name="x_add_log_note" widget="boolean_toggle"/>
                        <field name="x_partner_mobile" invisible="1"/>
                    </xpath>
                """
            })

    @api.model
    def get_values(self):
        values = super().get_values()
        values.update({
            'number_crm_config_ids': [
                (6, 0, self.env.company.sudo().number_crm_config_ids.ids)],
            'number_helpdesk_config_ids': [
                (6, 0, self.env.company.number_helpdesk_config_ids.ids)]
            if self.env.company.number_helpdesk_config_ids else False
        })
        return values

    def set_values(self):
        super().set_values()
        self.env.company.write({
            'number_crm_config_ids': [(6, 0, self.sudo().number_crm_config_ids.ids)],
            'number_helpdesk_config_ids': [(6, 0, self.number_helpdesk_config_ids.ids)]
        })

    def get_aircall_auth(self):
        """ Method for getting authentication values. """
        get_param = self.env['ir.config_parameter'].sudo().get_param
        url = get_param(
            'cit_aircall_api_integration.default_api_url',
            default='https://api.aircall.io')
        api_id = get_param(
            'cit_aircall_api_integration.default_api_id', default='dummy')
        api_token = get_param(
            'cit_aircall_api_integration.default_api_token', default='dummy')
        auth = False
        if get_param('cit_aircall_api_integration.aircall_auth', default=True):
            auth = AuthorizeAircallApi(url, api_id, api_token).get_authentication()
        return auth, url, api_id, api_token

    def create_update_number(self, NumObj, number, action):
        """Create or update Number record."""
        vals = {
            'number_id': number['id'],
            'name': number['name'],
            'direct_link': number['direct_link'],
            'digits': number['digits'],
            'country': number['country'],
            'tz': number['time_zone'],
            'open_status': number['open'],
            'availability_status': number['availability_status'],
            'priority': str(number['priority']) if number['priority'] else 'null',
            'is_ivr': number['is_ivr'],
            'live_recording_activated': number['live_recording_activated'],
        }
        return NumObj.create(vals) if action == 'create' else NumObj.write(vals)

    def fetch_numbers(self):
        """Method for fetch numbers from aircall to odoo."""
        auth, url, api_id, api_token = self.get_aircall_auth()
        NumObj = self.env['number.number']
        num_list = []
        if auth and auth.json():
            numbers = AuthorizeAircallApi(url, api_id, api_token).get_numbers()
            count = 0
            for number_data in numbers:
                for number in number_data.json()['numbers']:
                    count = count + 1
                    exist_num = NumObj.search([
                        ('number_id', '=', number['id']),
                        ('digits', '=', number['digits'])
                    ])
                    if not exist_num:
                        num_list.append(
                            self.create_update_number(NumObj, number, 'create').id)
                    else:
                        self.create_update_number(exist_num, number, 'write')
                        num_list.append(exist_num.id)
                    if num_list:
                        self.company_id.write({
                            'number_config_ids': [(6, 0, num_list)]
                        })
        elif auth.json() and auth.json().get('error'):
            raise ValidationError(_('Please %s', (auth.json().get('troubleshoot'))))

    def fetch_crm_numbers(self):
        """ Method for fetch numbers from aircall to odoo. """
        auth, url, api_id, api_token = self.get_aircall_auth()
        NumObj = self.env['number.number']
        num_list = []
        if auth and auth.json():
            numbers = AuthorizeAircallApi(url, api_id, api_token).get_numbers()
            count = 0
            for number_data in numbers:
                for number in number_data.json()['numbers']:
                    count = count + 1
                    exist_num = NumObj.search([
                        ('number_id', '=', number['id']),
                        ('digits', '=', number['digits'])])
                    if not exist_num:
                        num_list.append(
                            self.create_update_number(NumObj, number, 'create').id)
                    else:
                        self.create_update_number(exist_num, number, 'write')
                        num_list.append(exist_num.id)
                    if num_list:
                        self.company_id.write({
                            'number_crm_config_ids': [(6, 0, num_list)],
                            'number_config_ids': [(6, 0, num_list)]
                        })

        elif auth.json() and auth.json().get('error'):
            raise ValidationError(_('Please %s', (auth.json().get('troubleshoot'))))

    def fetch_helpdesk_numbers(self):
        """Method for fetch numbers from aircall to odoo."""
        auth, url, api_id, api_token = self.get_aircall_auth()
        NumObj = self.env['number.number']
        num_list = []
        if auth and auth.json():
            numbers = AuthorizeAircallApi(url, api_id, api_token).get_numbers()
            count = 0
            for number_data in numbers:
                for number in number_data.json()['numbers']:
                    count = count + 1
                    exist_num = NumObj.search([
                        ('number_id', '=', number['id']),
                        ('digits', '=', number['digits'])
                    ])
                    if not exist_num:
                        num_list.append(
                            self.create_update_number(NumObj, number, 'create').id)
                    else:
                        self.create_update_number(exist_num, number, 'write')
                        num_list.append(exist_num.id)
                    if num_list:
                        self.company_id.write({
                            'number_helpdesk_config_ids': [(6, 0, num_list)],
                            'number_config_ids': [(6, 0, num_list)]
                        })

        elif auth.json() and auth.json().get('error'):
            raise ValidationError(_('Please %s', (auth.json().get('troubleshoot'))))
