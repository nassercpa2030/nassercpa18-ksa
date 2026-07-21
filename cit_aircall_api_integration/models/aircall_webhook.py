# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

import logging
import time
import phonenumbers
import requests
import json
import pytz
import base64
import urllib.parse
from odoo.http import request
from markupsafe import Markup
from pytz import timezone
from datetime import datetime
from odoo import api, models
import re

_logger = logging.getLogger(__name__)

AIRCALL_API_URL = 'https://api.aircall.io/v1'


class AircallWebhook(models.TransientModel):
    _name = 'aircall.webhook'
    _description = 'Aircall Webhook'

    @api.model
    def message_events(self, payload):
        # Log full payload for debugging
        # _logger.info(f"[Aircall] Webhook payload received For SMS : {payload}")
        resource = payload.get("resource")
        event = payload.get("event")
        data = payload.get("data", {})
        config_tz = self.env['ir.config_parameter'].sudo().get_param(
            'cit_aircall_api_integration.timezone_setting') or 'UTC'
        tz = timezone(config_tz)
        timestamp = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
        if resource == "message":
            message_id = data.get("id")
            body = data.get("body", data.get("content", ""))
            contact_name = data.get("contact", {}).get("name", "Unknown")
            number = data.get("number", {})
            number_id = str(number.get("id")) if number.get("id") else False
            external_number = data.get("external_number", False)
            digits = number.get("digits", False)
            partner = self.env['res.partner'].sudo().search([
                ("phone", "ilike", digits)
            ], limit=1)
            if partner:
                vals = {
                    'message_id': message_id,
                    'body': body,
                    'contact_name': contact_name,
                    'external_number': external_number,
                    'digits': digits,
                    'number_id': number_id,
                    'timestamp': timestamp,
                }

                if event == "message.received":
                    vals.update({
                        'status': "Received",
                        'user_name': partner.name,
                        'user_email': partner.email,
                        'partner_id': partner.id,
                    })
                    self.env['aircall.message.history'].sudo().create(vals)

                elif event == "message.sent":
                    user = data.get("user", {})
                    vals.update({
                        'status': "Sent",
                        'ac_user_id': user.get('id'),
                        'user_name': user.get("name", False),
                        'user_email': user.get("email", False),
                    })
                    if partner:
                        vals['partner_id'] = partner.id
                    self.env['aircall.message.history'].sudo().create(vals)
                author_ref = self.env.ref(
                    'cit_aircall_api_integration.aircall_res_partner_1',
                    raise_if_not_found=False)
                author_id = author_ref.id if author_ref else None
            is_enabled_sms_chatter = self.env['ir.config_parameter'].sudo().get_param(
                'cit_aircall_api_integration.enable_sms_in_chatter')
            if partner and is_enabled_sms_chatter:
                direction = "Received" if event == "message.received" else "Sent"
                direction_text = (
                    f"<i class='fa fa-arrow-down text-success me-1'></i>Received from {external_number or 'N/A'}"
                    if direction == "Received" else
                    f"<i class='fa fa-arrow-up text-primary me-1'></i>Sent to {external_number or 'N/A'}"
                )
                sms_body = f"""
                <div class="mb-1 text-muted small">{direction_text}</div>
                <div class="o-mail-Message-textContent position-relative d-flex">
                    <div class="position-relative overflow-x-auto overflow-y-hidden d-inline-block text-body">
                        <div class="o-mail-Message-bubble rounded-bottom-3 position-absolute top-0 start-0 w-100 h-100 border {'o-green' if direction == 'Received' else 'o-primary'} rounded-end-3"></div>
                        <div class="position-relative text-break o-mail-Message-body mb-0 py-2 align-self-start rounded-end-3 rounded-bottom-3">
                            <p class="mb-0 o_mail_thread_message_content">{body or 'No content'}</p>
                        </div>
                        <div class="o-mail-Message-seenContainer position-absolute"></div>
                    </div>
                </div>
                """

                partner.sudo().message_post(
                    author_id=author_id if author_id else None,
                    body=Markup(sms_body))

                if self.env['ir.module.module'].sudo().search([
                    ('name', '=', 'crm'),
                    ('state', '=', 'installed')
                ]):
                    leads = self.env['crm.lead'].sudo().search([
                        ('partner_id', '=', partner.id)
                    ], limit=1)
                    for lead in leads:
                        lead.message_post(
                            author_id=author_id if author_id else None,
                            body=Markup(sms_body))

                if self.env['ir.module.module'].sudo().search([
                    ('name', '=', 'helpdesk'),
                    ('state', '=', 'installed')
                ]):
                    tickets = self.env['helpdesk.ticket'].sudo().search([
                        ('partner_id', '=', partner.id)
                    ], limit=1)
                    for ticket in tickets:
                        ticket.message_post(
                            author_id=author_id if author_id else None,
                            body=Markup(sms_body))

    @api.model
    def validate_webhook_token(self, token):
        """ Method for validate the aircall webhook token. """
        true_token = self.env['ir.config_parameter'].sudo(
        ).get_param('cit_aircall_api_integration.default_aircall_integration_token')
        if true_token is False:
            _logger.warning(
                'Aircall integration token has not been set. '
                'Webhooks cannot work without it.')
        return true_token == token

    @api.model
    def get_aircall_api_config(self):
        """Will throw an error if the config is not set."""
        sudo_param = self.sudo().env['ir.config_parameter']
        return sudo_param.get_param(
            'cit_aircall_api_integration.default_api_id'), sudo_param.get_param(
            'cit_aircall_api_integration.default_api_token')

    @api.model
    def register(self, payload):
        """ Method where all webhook events are defined. """
        register_map = {
            'call.created': self._send_insight_card,
            'call.ended': self._register_call,
            'call.commented': self._register_comment,
            'contact.created': self._register_contact,
        }
        try:
            method = register_map[payload['event']]
        except KeyError:
            return
        method(payload)

    def fetch_transcription(self, call_id):
        """Fetch call transcription and return the utterances list."""
        api_id, api_token = self.get_aircall_api_config()
        if False in [api_id, api_token]:
            _logger.warning(
                "Aircall api credentials are not set. Some features won't work")
            return None

        url = f"{AIRCALL_API_URL}/calls/{call_id}/transcription"
        try:
            response = requests.get(url, auth=(api_id, api_token))
            response.raise_for_status()
            transcription_data = response.json()
            transcription = transcription_data.get('transcription', {})

            utterances = []
            for utterance in transcription.get('content', {}).get('utterances', []):
                utterance_data = {
                    'time_range': f"{utterance.get('start_time', 0):.2f}s - {utterance.get('end_time', 0):.2f}s",
                    'speaker': f"{utterance.get('participant_type', 'N/A').capitalize()} ({utterance.get('phone_number', 'N/A')})",
                    'text': utterance.get('text', 'N/A')
                }
                utterances.append(utterance_data)
            return utterances

        except requests.RequestException as e:
            return None

    def fetch_summary(self, call_id):
        """Fetch call summary and return the summary content as a string."""
        api_id, api_token = self.get_aircall_api_config()
        if False in [api_id, api_token]:
            _logger.warning(
                "Aircall api credentials are not set. Some features won't work")
            return None

        url = f"{AIRCALL_API_URL}/calls/{call_id}/summary"
        try:
            response = requests.get(url, auth=(api_id, api_token))
            response.raise_for_status()  # Raises an error for bad status codes
            summary_data = response.json()
            summary_content = summary_data.get('summary', {}).get('content', '')
            return summary_content  # Returns the summary content as a string
        except requests.RequestException as e:
            return None

    def fetch_key_topics(self, call_id):
        """Fetch key topics of a call and return them as a list of strings."""
        api_id, api_token = self.get_aircall_api_config()
        if False in [api_id, api_token]:
            _logger.warning(
                "Aircall API credentials are not set. Some features won't work.")
            return None

        url = f"{AIRCALL_API_URL}/calls/{call_id}/topics"
        try:
            response = requests.get(url, auth=(api_id, api_token))
            response.raise_for_status()
            data = response.json()
            topics = data.get('topic', []).get('content', "")
            return topics
        except requests.RequestException as e:
            return None

    def fetch_sentiment(self, call_id):
        """Fetch sentiment of a call and return the sentiment as a string."""
        api_id, api_token = self.get_aircall_api_config()
        if False in [api_id, api_token]:
            _logger.warning(
                "Aircall API credentials are not set. Some features won't work.")
            return None

        url = f"{AIRCALL_API_URL}/calls/{call_id}/sentiments"
        try:
            response = requests.get(url, auth=(api_id, api_token))
            response.raise_for_status()
            data = response.json()
            sentiment_value = data['sentiment']['participants'][0]['value']
            return sentiment_value
        except requests.RequestException as e:
            return None

    def create_call_detail(
            self, call_id, recording, waiting_time, i, mail_data, data,
            talk_time, tags, comments):
        setting_peram = self.env['ir.config_parameter'].sudo()
        enable_transcription = setting_peram.get_param(
            'cit_aircall_api_integration.enable_transcription_feature') == 'True'
        enable_summary = setting_peram.get_param(
            'cit_aircall_api_integration.enable_summary_feature') == 'True'

        aircall_transcription = self.fetch_transcription(call_id) if enable_transcription else False
        aircall_summary = self.fetch_summary(call_id) if enable_summary else False
        key_topics = self.fetch_key_topics(call_id) if enable_summary else False
        sentiment = self.fetch_sentiment(call_id) if enable_summary else False
        number = data['number']['digits'] if data.get('number') and data['number'].get(
            'digits') else ''

        if i and hasattr(i, 'parent_id'):
            parents = i.mapped('parent_id').filtered(lambda p: p.active).ids if i else False
            last_parent = parents[-1] if parents else i  # If no parent, fallback to `i`
        else:
            last_parent = i  # If `i` doesn't have `parent_id`, fallback to `i`

        if not self.env['aircall.details'].sudo().search_count([
            ('aircall_call_id', '=', call_id)
        ]):
            self.env['aircall.details'].sudo().create({
                'aircall_call_id': call_id,
                 'call_by_user': self._get_display_user(data),
                'customer_id': last_parent.id if last_parent else False,
                'recording_url': recording,
                'phonenumbers': data['raw_digits'],
                'call_qualification': data['direction'],
                'call_duration': time.strftime(
                    '%H:%M:%S', time.gmtime(data['duration'])),
                'waiting_time': waiting_time,
                'call_time': talk_time,
                'air_call_number': number,
                'tags': tags,
                'notes': comments and comments[0] or '',
                'aircall_transcription': aircall_transcription or 'No Transcription Available' if enable_transcription else '',
                'aircall_summary': aircall_summary or 'No Summary Available For this Call' if enable_summary else '',
                'sentiments': sentiment or 'No Sentiments Detected' if enable_summary else '',
                'key_topics': key_topics or 'No Key Points Available' if enable_summary else '',
            })

        if tags and i:
            # Prepare a list of sanitized tags
            tag_list = [tag.strip() for tag in tags if isinstance(tag, str) and tag.strip()]
            if self.env.context.get('from_res_partner'):
                for tag in tag_list:
                    # Fetch or create the partner category
                    category = self.env['res.partner.category'].sudo().search([
                        ('name', '=', tag)
                    ],
                        limit=1)
                    if not category:
                        category = self.env['res.partner.category'].sudo().create({
                            'name': tag
                        })

                    # Append the category to the category_id field
                    i.sudo().write({
                        'category_id': [(4, category.id)]
                    })

            # Fetch configuration setting for Helpdesk tickets
            helpdesk_ticket = self.env['ir.config_parameter'].sudo().get_param(
                'cit_aircall_api_integration.helpdesk_log_note_setting')

            # Check if the CRM module is installed before accessing crm.tag
            if self.env['ir.module.module'].sudo().search([
                ('name', '=', 'crm'),
                ('state', '=', 'installed')
            ]):
                # Fetch or create CRM tags and append them to the last created CRM lead
                crm_tag_ids = []
                for tag in tag_list:
                    tag_rec = self.env['crm.tag'].sudo().search([
                        ('name', '=', tag)
                    ], limit=1)
                    if not tag_rec:
                        tag_rec = self.env['crm.tag'].sudo().create({
                            'name': tag
                        })
                    crm_tag_ids.append(tag_rec.id)

                last_crm_lead = self.env['crm.lead'].sudo().search([
                    ('partner_id', '=', i.id)
                ], order='create_date desc', limit=1)
                if last_crm_lead:
                    for tag_id in crm_tag_ids:
                        last_crm_lead.sudo().write({
                            'tag_ids': [(4, tag_id)]
                        })
                    last_crm_lead._cr.commit()

            # Logic for Helpdesk tickets
            if helpdesk_ticket == 'open_new_ticket':
                helpdesk_tag_ids = []
                for tag in tag_list:
                    tag_rec = self.env['helpdesk.tag'].sudo().search([
                        ('name', '=', tag)
                    ], limit=1)
                    if not tag_rec:
                        tag_rec = self.env['helpdesk.tag'].sudo().create({
                            'name': tag
                        })
                    helpdesk_tag_ids.append(tag_rec.id)

                last_helpdesk_ticket = self.env['helpdesk.ticket'].sudo().search([],
                                                                                 order='create_date desc', limit=1)
                if last_helpdesk_ticket:
                    for tag_id in helpdesk_tag_ids:
                        last_helpdesk_ticket.sudo().write({
                            'tag_ids': [(4, tag_id)]
                        })
                    last_helpdesk_ticket._cr.commit()

            elif helpdesk_ticket == 'add_log_note_exciting':
                tickets_with_log_note = self.env['helpdesk.ticket'].sudo().search([
                    ('x_add_log_note', '=', True)
                ])
                if tickets_with_log_note:
                    helpdesk_tag_ids = []
                    for tag in tag_list:
                        tag_rec = self.env['helpdesk.tag'].sudo().search([
                            ('name', '=', tag)
                        ], limit=1)
                        if not tag_rec:
                            tag_rec = self.env['helpdesk.tag'].sudo().create({
                                'name': tag
                            })
                        helpdesk_tag_ids.append(tag_rec.id)

                    for ticket in tickets_with_log_note:
                        for tag_id in helpdesk_tag_ids:
                            ticket.sudo().write({
                                'tag_ids': [(4, tag_id)]
                            })
                    self._cr.commit()

    @api.model
    def _register_comment(self, payload):
        """Method called when notes being noted to the call."""
        comments = []
        data = payload.get('data')
        for comment in data.get('comments'):
            comments.append('\n{}'.format(comment.get('content')))
        call_comment = "\n".join(comments)
        aircall_detail_rec = self.env['aircall.details'].sudo().search([
            ('aircall_call_id', '=', data.get('id'))
        ], order='id desc', limit=1)
        if aircall_detail_rec:
            if call_comment and not aircall_detail_rec.notes:
                # _logger.info(
                #     '\n\nAircallDetailRec-Comment %s', aircall_detail_rec,
                #     aircall_detail_rec.notes)
                aircall_detail_rec.sudo().write({
                    'notes': call_comment
                })

    def _process_comments_tags(self, data):
        """Used to Comments and Tags which is added During the call."""
        comments = [f"\n{comment['content']}" for comment in data['comments']]
        tags = [f"\n{tag['name']}" for tag in data['tags']]
        return comments, tags

    def _process_call_with_conf_num(self, payload, comments, tags):
        """Used to allows user to add the logout which is configured in setting."""
        data = payload['data']
        partner_obj = self.env['res.partner'].sudo()
        external_entity_ids = self._find_partner(partner_obj, data['raw_digits'])

        # Check if message is already logged for this call ID
        check_msg = self.env['mail.message'].sudo().search_count(
            [('aircall_call_id', '=', data['id'])], limit=1
        )

        manual_call_loging = self.env['ir.config_parameter'].sudo().get_param(
            'cit_aircall_api_integration.manual_call_loging')

        if not check_msg and payload.get(
                'event') == 'call.ended' and external_entity_ids:
            talk_time, waiting_time = self._calculate_times(data)
            message = self._generate_message(
                data, talk_time, waiting_time, tags, comments)

            for partner in external_entity_ids:
                if not manual_call_loging or partner.x_add_log_note:
                    self._post_message_and_create_call(
                        partner, message, data, talk_time, waiting_time, tags, comments)
                    partner.update({
                        'x_add_log_note': False
                    })  # Reset the flag after posting

    def _process_call_without_conf_num(self, data):
        """Used to calls when call is disconnected."""
        partner_obj = self.env['res.partner']
        external_entity_ids = self._find_partner(
            partner_obj, data['raw_digits']).filtered(lambda a: a.x_add_log_note)
        if external_entity_ids:
            [external_entity_id.update({
                'x_add_log_note': False
            }) for external_entity_id in external_entity_ids]

    @api.model
    def _register_call(self, payload):
        """Used for when a call event is performed,
        handling general call processing, CRM leads, and Helpdesk tickets."""
        # _logger.info(payload)
        assert payload['resource'] == 'call'

        data = payload['data']
        company = request.env.company
        number = data['number']

        if data and self.env['mail.message'].sudo().search_read([
            ('aircall_call_id', '=', data['id'])
        ], limit=1):
            return True

        # Common data processing
        conf_num = self.sudo()._get_conf_num(company.sudo(), number)

        comments, tags = self._process_comments_tags(data)

        if conf_num:
            self._process_call_with_conf_num(payload, comments, tags)
        else:
            self._process_call_without_conf_num(data)

        # Check if CRM module is installed
        crm_installed = self.env['ir.module.module'].sudo().search_count([
            ('name', '=', 'crm'),
            ('state', '=', 'installed')
        ]) > 0

        enable_helpdesk_module = self.env['ir.config_parameter'].sudo().get_param(
            'cit_aircall_api_integration.enable_helpdesk_module')

        if crm_installed:
            # Handle CRM leads
            crm_lead = self.env['crm.lead'].sudo().search([
                ('partner_id', '!=', False),
                '|', ('phone', 'ilike', data['raw_digits']),
                '|', ('phone', 'ilike', data['raw_digits'].replace(" ", "")),
                '|', ('mobile', 'ilike', data['raw_digits']),
                ('mobile', 'ilike', data['raw_digits'].replace(" ", ""))
            ])
            self._process_leads(crm_lead, data, tags, comments)
        else:
            _logger.warning("CRM module is not installed, skipping CRM lead processing.")

        # Check if Helpdesk module is installed
        helpdesk_installed = self.env['ir.module.module'].sudo().search_count([
            ('name', '=', 'helpdesk'),
            ('state', '=', 'installed')
        ]) > 0

        if helpdesk_installed and enable_helpdesk_module:
            helpdesk = self.env['helpdesk.ticket'].sudo().search([
                '|',
                ('partner_phone', 'ilike', data['raw_digits']),
                '|',
                ('partner_phone', 'ilike', data['raw_digits'].replace(" ", "")),
                '|',
                ('x_partner_mobile', 'ilike', data['raw_digits']),
                ('x_partner_mobile', 'ilike', data['raw_digits'].replace(" ", "")),
                ('x_add_log_note', '=', True)
            ])
            self._process_helpdesk(helpdesk, data, tags, comments)
        else:
            _logger.warning(
                "Helpdesk module is not installed, skipping Helpdesk ticket processing.")

        return True

    def _get_conf_num(self, company, number):
        """Fetches configuration numbers based on the company's number config."""
        if not company.sudo().number_config_ids:
            return []
        num_search = self.env['number.number'].sudo().search([
            ('id', 'in', company.sudo().number_config_ids.ids)
        ])
        conf_num = [num for num in num_search if
                    str(num.number_id) == str(number['id']) and str(num.digits) == str(
                        number['digits'])]
        return conf_num

    def _process_helpdesk(self, helpdesk, data, tags, comments):
        """Used for adding a log note in ticket for configured aircall user."""
        for rec in helpdesk:
            talk_time, waiting_time = self._calculate_times(data)
            if self._is_helpdesk_number_configured(data['number']['digits']):
                message = self._generate_message(
                    data, talk_time, waiting_time, tags, comments)
                author_ref = self.env.ref(
                    'cit_aircall_api_integration.aircall_res_partner_1',
                    raise_if_not_found=False)
                author_id = author_ref.id if author_ref else None
                mail_data = rec.sudo().message_post(
                    body=message, author_id=author_id if author_id else None)
                if mail_data:
                    mail_data.aircall_call_id = data['id']
                    self.create_call_detail(
                        data['id'], data['asset'], waiting_time, rec, mail_data,
                        data, talk_time, tags, comments)
        helpdesk.sudo().write({
            'x_add_log_note': False
        })

    def _is_helpdesk_number_configured(self, digits):
        """Find the configure aircall number in setting."""
        return self.env.company.sudo().number_helpdesk_config_ids.filtered(
            lambda num: num.digits == digits)

    def _find_partner(self, partner_obj, raw_digits):
        """Finds the external entity based on the phone or mobile number."""
        return partner_obj.sudo().search([
            '|',
            ('phone', 'ilike', raw_digits),
            '|',
            ('phone', 'ilike', raw_digits.replace(" ", "")),
            '|',
            ('mobile', 'ilike', raw_digits),
            ('mobile', 'ilike', raw_digits.replace(" ", ""))
        ], order='id desc')

    def _handle_unknown_contact_creation(self, external_entity_id, partner_obj, data):
        """Handles the creation of unknown contacts if allowed."""
        create_aircall_contact = self.env['ir.config_parameter'].sudo().get_param(
            'cit_aircall_api_integration.allow_create_unknown_contacts')

        if create_aircall_contact and not external_entity_id:
            aircall_contact_find = self._find_partner(partner_obj, data['raw_digits'])
            if not aircall_contact_find:
                external_entity_id = partner_obj.sudo().create({
                    'name': "NEW : " + data['raw_digits'],
                    'phone': data['raw_digits'],
                    'email': '',
                })

        for partner in external_entity_id:
            if len(external_entity_id) == 1 and not partner.x_add_log_note:
                partner.x_add_log_note = True

        return external_entity_id

    def _calculate_times(self, data):
        """Calculates the talk time and waiting time based on call data."""
        talk_time = waiting_time = 0
        if data['answered_at']:
            talk_time = time.strftime(
                '%H:%M:%S', time.gmtime(data['ended_at'] - data['answered_at']))
            waiting_time = time.strftime(
                '%H:%M:%S', time.gmtime(data['answered_at'] - data['started_at']))

        return talk_time, waiting_time

    def _get_display_user(self, data):
        user = data.get("user") or {}
        if user.get("name"):
            return user["name"]

        number = data.get("number") or {}
        if number.get("name"):
            return number["name"]

        return "Not Assigned"

    @api.model
    def _generate_message(self, data, talk_time, waiting_time, tags, comments):
        call_id = data.get("id", "")
        sentiment = None
        formatted_key_points = None
        summary = None
        if self.env['ir.config_parameter'].sudo().get_param(
                'cit_aircall_api_integration.enable_summary_feature'):
            summary = self.fetch_summary(call_id)
            key_points = self.fetch_key_topics(call_id)
            formatted_key_points = None
            if key_points:
                formatted_key_points = "<ul>"
                for topic in key_points:
                    formatted_key_points += f"<li>{topic}</li>"
                formatted_key_points += "</ul>"
                formatted_key_points = Markup(formatted_key_points)
            sentiment = self.fetch_sentiment(call_id)
            """Generates the message using the timezone 
            configured in ResConfigSettings."""

        config_tz = self.env['ir.config_parameter'].sudo().get_param(
            'cit_aircall_api_integration.timezone_setting') or 'UTC'

        try:
            display_tz = pytz.timezone(config_tz)
        except pytz.UnknownTimeZoneError:
            display_tz = pytz.UTC

        started_at_utc = datetime.utcfromtimestamp(
            int(data['started_at'])).replace(tzinfo=pytz.utc)
        ended_at_utc = datetime.utcfromtimestamp(
            int(data['ended_at'])).replace(tzinfo=pytz.utc)

        started_at = started_at_utc.astimezone(
            display_tz).strftime('%A %b %d %Y (%I:%M:%S %p)')
        ended_at = ended_at_utc.astimezone(
            display_tz).strftime('%A %b %d %Y (%I:%M:%S %p)')

        missed_call_status = 'No' if data.get('answered_at') else 'Yes'

        aircall_user = self._get_display_user(data)
        html = f"""
        <strong>Call ID:</strong> {call_id}<br/>
        <strong>Started At:</strong> {started_at}<br/>
        <strong>Ended At:</strong> {ended_at}<br/>
        <strong>Contact Number:</strong> {data.get("raw_digits", "")}<br/>
        <strong>Call direction:</strong> {data.get("direction", "")}<br/>
        <strong>Aircall User:</strong> {aircall_user}<br/>
        <strong>Aircall Number:</strong> {data.get("number", {}).get("digits", "")}<br/>
        <strong>Call Duration:</strong> {data.get('duration', 0)} Sec<br/>
        <strong>Missed Call:</strong> {missed_call_status}<br/>
        <strong>Tags:</strong> {", ".join(tags)}<br/>
        <strong>Comments:</strong> {" ".join(comments)}<br/>
        """
        sentiment_emoji = {
            'POSITIVE': '🙂',
            'NEGATIVE': '😡',
            'NEUTRAL': '😐'
        }

        if sentiment:
            emoji = sentiment_emoji.get(sentiment.upper(), '❓')
            html += f"<strong>Mood :</strong>{sentiment.capitalize() if sentiment else  'No Valid Data Found' } {emoji if emoji else '' }<br/>"

        if summary:
            html += f"<strong>Summary :</strong> {summary if summary else 'No Valid Summary' }<br/>"

        if formatted_key_points:
            html += f"<strong>Key Points :</strong> {formatted_key_points if formatted_key_points else 'No Key Topics Found' } <br/>"

        return Markup(html)

    def _post_message_and_create_call(
            self, partner, message, data, talk_time, waiting_time, tags, comments):
        """Posts a message and creates the call detail entry."""
        author_ref = self.env.ref(
            'cit_aircall_api_integration.aircall_res_partner_1', raise_if_not_found=False)
        author_id = author_ref.id if author_ref else None
        manual_call_loging = self.env['ir.config_parameter'].sudo().get_param(
            'cit_aircall_api_integration.manual_call_loging')

        partner_matches = self.env['res.partner'].sudo().search([
            '|',
            ('phone', 'ilike', data['raw_digits']),
            '|',
            ('phone', 'ilike', data['raw_digits'].replace(" ", "")),
            '|',
            ('mobile', 'ilike', data['raw_digits']),
            ('mobile', 'ilike', data['raw_digits'].replace(" ", ""))
        ])

        all_parent_ids = partner_matches.ids + partner_matches.mapped('parent_id').filtered(lambda p: p.active).ids
        if all_parent_ids:
            existing_log = self.env['mail.message'].sudo().search([
                ('aircall_call_id', '=', data['id']),
                ('res_id', 'in', all_parent_ids),
                ('model', '=', 'res.partner')
            ], limit=1)
            if existing_log:
                return

        mail_data = None  # Initialize mail_data to avoid UnboundLocalError
        message_partner = partner
        if not manual_call_loging and len(partner_matches) > 1:
            # Multiple partners found, log message for the last parent's contact if any
            parents = partner_matches.mapped('parent_id').filtered(lambda p: p.active)
            if parents:
                last_parent = parents.sorted(lambda p: p.create_date, reverse=True)[:1]
                message_partner = last_parent
            else:
                last_partner = partner_matches.sorted(lambda p: p.create_date, reverse=True)[:1]
                message_partner = last_partner
        mail_data = message_partner.sudo().message_post(
            body=message,
            author_id=author_id
        )
        # Process mail_data and create call detail
        if mail_data:
            mail_data.aircall_call_id = data['id']
            partner.sudo().write({'x_add_log_note': False})  # Reset add_log_note

            final_partner = message_partner

            self.with_context(from_res_partner=True).create_call_detail(
                data['id'], data['asset'], waiting_time, final_partner, mail_data, data, talk_time,
                tags, comments
            )

    @api.model
    def _send_insight_card(self, payload):
        """Method for sending the insight card."""
        api_id, api_token = self.get_aircall_api_config()
        if False in [api_id, api_token]:
            _logger.warning(
                "Aircall api credentials are not set. Some features won't work")
            return
        json_field = self._populate_insight_card(payload)
        if json_field is False:
            # Callee was not found on the system on the system
            return
        aircall_url = AIRCALL_API_URL + "/calls/" + str(
            payload['data']['id']) + "/insight_cards"
        requests.post(
            aircall_url, auth=(api_id, api_token), json=json_field)

    def _get_helpdesk_ticket(self, raw_digits):
        """Fetch Helpdesk ticket by partner's phone or mobile number
        only if Helpdesk is installed. """
        helpdesk_installed = self.env['ir.module.module'].sudo().search_count([
            ('name', '=', 'helpdesk'),
            ('state', '=', 'installed')
        ]) > 0
        enable_helpdesk_module = self.env['ir.config_parameter'].sudo().get_param(
            'cit_aircall_api_integration.enable_helpdesk_module')

        if not helpdesk_installed:
            return self.env['ir.model.data'].browse()

        if helpdesk_installed and enable_helpdesk_module:
            return self.env['helpdesk.ticket'].sudo().search([
                '|',
                ('partner_phone', 'ilike', raw_digits),
                '|',
                ('partner_phone', 'ilike', raw_digits.replace(" ", "")),
                '|',
                ('x_partner_mobile', 'ilike', raw_digits),
                ('x_partner_mobile', 'ilike', raw_digits.replace(" ", ""))
            ])

    @api.model
    def _populate_insight_card(self, payload):
        """Method for populating the insight card to the current call, handling CRM,
        interactions, and Helpdesk."""
        data = payload['data']

        # Ensure Helpdesk module is installed before proceeding
        helpdesk_installed = self.env['ir.module.module'].sudo().search_count([
            ('name', '=', 'helpdesk'),
            ('state', '=', 'installed')
        ]) > 0

        enable_helpdesk_module = self.env['ir.config_parameter'].sudo().get_param(
            'cit_aircall_api_integration.enable_helpdesk_module')

        # Search for partner based on phone number
        partner = self.env['res.partner'].sudo().search([
            '|',
            ('phone', 'ilike', data['raw_digits']),
            '|',
            ('phone', 'ilike', data['raw_digits'].replace(" ", "")),
            '|',
            ('mobile', 'ilike', data['raw_digits']),
            ('mobile', 'ilike', data['raw_digits'].replace(" ", ""))
        ])

        manual_call_loging = self.env['ir.config_parameter'].sudo().get_param(
            'cit_aircall_api_integration.manual_call_loging')
        enable_crm_module = self.env['ir.config_parameter'].sudo().get_param(
            'cit_aircall_api_integration.enable_crm_module')

        if data.get('direction') == 'inbound':
            partner = self._handle_unknown_contact_creation(
                partner, self.env['res.partner'], data)

        if manual_call_loging:
            partner_name_string = 'Click to log call'
        else:
            last_partner = partner.sorted(
                key=lambda p: p.create_date, reverse=True)[0] if partner else None
            if last_partner:
                partner_name_string = last_partner.name
                parents = last_partner.parent_id and [last_partner.parent_id] or []
                if parents:
                    last_partner = parents[-1]
                    partner_name_string = last_partner.name
            else:
                partner_name_string = 'No partners found'

        if len(partner) == 1:
            partner_name_string = partner.name
            partner.write({
                'x_add_log_note': True
            })

        # Handle CRM leads only if CRM module is enabled
        leads_text = 'Create new opportunity'
        lead = False  # Initialize lead here
        if enable_crm_module == 'True':
            lead = self._get_crm_lead(data['raw_digits'])
            if lead:
                if manual_call_loging:
                    leads_text = 'Click to log call'
                elif manual_call_loging is False:
                    parent_opportunity = self.env['crm.lead'].sudo().search([
                        ('partner_id', 'in', partner.mapped('parent_id').ids)
                    ], order='id desc', limit=1)
                    if parent_opportunity:
                        leads_text = parent_opportunity.name
                    else:
                        child_opportunity = self.env['crm.lead'].sudo().search([
                            ('partner_id', 'in', partner.ids)
                        ], order='id desc', limit=1)
                        leads_text = child_opportunity.name if child_opportunity else 'No lead found'
                else:
                    leads_text = 'Select Opportunity'

                if len(lead) == 1 and partner:
                    leads_text = f"{lead[0].name}"

        # Generate initial JSON response
        json_field = self._generate_insight_card_json(partner, partner_name_string, data)
        if not json_field:
            return False

        # Extend with lead information only if CRM module is enabled
        if enable_crm_module == 'True':
            last_partner = partner.sorted(
                key=lambda p: p.create_date, reverse=True)[0] if partner else None
            result = self._extend_card_with_lead_info(
                json_field, lead, leads_text, last_partner)
        else:
            result = json_field

        # Custom logic for Helpdesk tickets only if module is installed and enabled
        if helpdesk_installed and enable_helpdesk_module == 'True':
            helpdesk = self._get_helpdesk_ticket(data['raw_digits']) or self.env['helpdesk.ticket']
            helpdesk_text = 'Select Ticket'
            partner = self._find_partner(
                self.env['res.partner'], data['raw_digits']) or self.env['res.partner']

            if len(helpdesk) == 1 and partner:
                helpdesk_text = helpdesk.name

            result = self._extend_card_with_helpdesk_info(
                result, helpdesk, helpdesk_text, partner[0] if partner else None)

        return result

    def _extend_card_with_helpdesk_info(self, result, ticket_ids, helpdesk_text, partner):
        """Extend insight card with Helpdesk info using
        /odoo/all-tickets and direct form view."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        enable_helpdesk = self.env['ir.config_parameter'].sudo().get_param(
            'cit_aircall_api_integration.enable_helpdesk_module') == 'True'

        if not enable_helpdesk:
            return result

        helpdesk_installed = self.env['ir.module.module'].sudo().search_count([
            ('name', '=', 'helpdesk'),
            ('state', '=', 'installed')
        ]) > 0

        if not helpdesk_installed:
            return result

        helpdesk_setting = self.env['ir.config_parameter'].sudo().get_param(
            'cit_aircall_api_integration.helpdesk_log_note_setting')
        if not partner:
            return result

        url = False
        context = {
            'default_partner_id': partner.id,
            'default_name': 'Ticket of ' + (partner.name or 'Unknown')
        }
        context_str = urllib.parse.quote(json.dumps(context))
        if helpdesk_setting == 'open_new_ticket':
            ticket = self.env['helpdesk.ticket'].sudo().create({
                'partner_id': partner.id,
                'name': f"Ticket of {partner.name or 'Unknown'}",
                'x_add_log_note': True
            })
            url = f"{base_url}/odoo/all-tickets/{ticket.id}?context={context_str}"

        elif helpdesk_setting == 'add_log_note_exciting':
            if ticket_ids and len(ticket_ids) == 1:
                url = f"{base_url}/odoo/all-tickets/{ticket_ids.ids[0]}?context={context_str}"
            elif ticket_ids and len(ticket_ids) > 1:
                domain = [('id', 'in', ticket_ids.ids)]
                domain_str = base64.urlsafe_b64encode(json.dumps(domain).encode()).decode()
                url = f"{base_url}/odoo/all-tickets?view_type=list&context={context_str}&aircall_domain={domain_str}"
            else:
                domain = [('id', '=', False)]
                domain_str = base64.urlsafe_b64encode(json.dumps(domain).encode()).decode()
                url = f"{base_url}/odoo/all-tickets?view_type=list&context={context_str}&aircall_domain={domain_str}"

        if url:
            result['contents'].append({
                'type': 'shortText',
                'label': 'Ticket',
                'text': helpdesk_text,
                'link': url
            })

        return result

    def _generate_insight_card_json(self, partner, partner_name_string, data):
        """Generate main insight card with Contact info and /odoo/contacts link."""
        partner = partner[0] if isinstance(partner, list) else partner
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        url = ""
        if len(partner) == 1:
            url = f"{base_url}/web#id={partner.id}&model=res.partner&view_type=form"
        else:
            action_vals = {
                'name': 'Contact',
                'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'view_mode': 'list,form',
                'view_id': False,
                'domain': [('id', 'in', partner.ids)],
                'target': 'current',
            }
            action = self.env['ir.actions.act_window'].sudo().create(action_vals)
            url = f"{base_url}/web#action={action.id}&model=res.partner"

        return {
            'contents': [
                {
                    'type': 'title',
                    'text': 'Odoo information',
                    'link': url,
                },
                {
                    'type': 'shortText',
                    'label': 'Contact',
                    'text': partner_name_string,
                    'link': url,
                }
            ]
        }

    @api.model
    def _register_contact(self, payload):
        """ Method called when contact is created in Aircall. """
        # _logger.info(payload)
        phone_format = ''
        res_partner = self.env['res.partner']
        phone_details = self.env['phone.details']
        email_details = self.env['email.details']
        contact = payload['data']
        company = False

        if contact.get('phone_numbers'):
            phone = phonenumbers.parse(contact.get('phone_numbers')[0]['value'])
            phone_format = phonenumbers.format_number(
                phone, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            phone_format_clean = phone_format.replace(" ", "").replace("-", "")

        partner = False
        if phone_format:
            phone_clean = phone_format.replace(" ", "").replace("-", "")
            partner = res_partner.sudo().search([
                '|', '|',
                ('phone', 'in', [phone_format, phone_clean]),
                ('mobile', 'in', [phone_format, phone_clean]),
                ('phone', 'like', phone_format_clean),
            ], limit=1)

        if not partner:
            # Create company if it is not exists
            if contact.get('company_name'):
                company = res_partner.sudo().search([
                    ('name', '=', contact.get('company_name'))
                ], limit=1)
                if not company:
                    company = res_partner.sudo().create({
                        'name': contact.get('company_name'),
                        'company_type': 'company',
                        'is_company': True,
                        'aircall_id': contact.get('id'),
                        'from_register_contact': True
                    })

            # Create new partner
            partner = res_partner.sudo().create({
                'name': contact.get('first_name'),
                'last_name': contact.get('last_name') or '',
                'comment': contact.get('information'),
                'phone': phone_format if contact.get('phone_numbers') else '',
                'mobile': phone_format if contact.get('phone_numbers') else '',
                'email': contact['emails'][0]['value'] if contact.get('emails') else '',
                'parent_id': company and company.id or False,
                'aircall_id': contact.get('id'),
                'direct_link': contact.get('direct_link'),
                'is_shared': contact.get('is_shared'),
                'from_register_contact': True,
            })

        # Update phone details
        for phone in contact.get('phone_numbers'):
            parsed_phone = phonenumbers.parse(phone['value'])
            formatted_phone = phonenumbers.format_number(
                parsed_phone, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            formatted_phone_clean = formatted_phone.replace(" ", "").replace("-", "")
            # Check if phone already exists for this partner
            existing_phone = phone_details.sudo().search([
                ('partner_id', '=', partner.id),
                ('value', 'in', [formatted_phone, formatted_phone_clean])
            ], limit=1)
            if not existing_phone:
                phone_details.sudo().create({
                    'phone_id': phone['id'],
                    'label': phone['label'],
                    'value': formatted_phone,
                    'partner_id': partner.id,
                })

        # Update email details
        for email in contact.get('emails'):
            existing_email = email_details.sudo().search([
                ('partner_id', '=', partner.id),
                ('value', '=', email['value'])
            ], limit=1)
            if not existing_email:
                email_details.sudo().create({
                    'email_id': email['id'],
                    'label': email['label'],
                    'value': email['value'],
                    'partner_id': partner.id,
                })

    def _get_crm_lead(self, raw_digits):
        """ Fetch CRM lead by phone or mobile number only if CRM is installed. """
        crm_installed = self.env['ir.module.module'].sudo().search_count([
            ('name', '=', 'crm'), ('state', '=', 'installed')
        ]) > 0

        if not crm_installed:
            return self.env['ir.model.data'].browse()  # Returns an empty recordset safely

        return self.env['crm.lead'].sudo().search([
            ('partner_id', '!=', False),
            '|', ('phone', 'ilike', raw_digits),
            '|', ('phone', 'ilike', raw_digits.replace(" ", "")),
            '|', ('mobile', 'ilike', raw_digits),
            ('mobile', 'ilike', raw_digits.replace(" ", "")),
        ])

    def _extend_card_with_lead_info(self, result, lead, leads_text, partner):
        """Extend insight card with lead information using
        /odoo/crm and proper view redirection."""
        # _logger.info("Processing lead information for partner: %s", partner)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        crm_installed = self.env['ir.module.module'].sudo().search_count([
            ('name', '=', 'crm'),
            ('state', '=', 'installed')
        ]) > 0

        if not crm_installed:
            _logger.warning("CRM module is not installed.")
            return result

        try:
            self.sudo().env.ref('crm.crm_lead_opportunities')
        except ValueError:
            _logger.warning("External ID 'crm.crm_lead_opportunities' not found.")
            return result

        if not partner:
            return result

        lead_ids = lead.ids if lead else []
        context = {
                'default_partner_id': partner.id,
                'default_name': f'Opportunity of {partner.name}'
            }
        context_str = urllib.parse.quote(json.dumps(context))
        if lead_ids and len(lead_ids) == 1:
            url = f"{base_url}/odoo/crm/{lead_ids[0]}?context={context_str}&view_type=form"
        elif lead_ids and len(lead_ids) > 1:
            domain = [('id', 'in', lead_ids)]
            domain_str = base64.urlsafe_b64encode(json.dumps(domain).encode()).decode()
            url = f"{base_url}/odoo/crm?view_type=list&context={context_str}&view_mode=list&aircall_domain={domain_str}"
        else:
            domain = [('id', '=', False)]
            domain_str = base64.urlsafe_b64encode(json.dumps(domain).encode()).decode()
            url = f"{base_url}/odoo/crm?view_type=list&context={context_str}&view_mode=list&aircall_domain={domain_str}"

        result['contents'].append({
            'type': 'shortText',
            'label': 'Opportunity',
            'text': leads_text,
            'link': url
        })

        # _logger.info("Updated result: %s", result)
        return result

    def _is_number_configured(self, digits):
        """Find the configure aircall number in setting"""
        return self.env.company.sudo().number_crm_config_ids.sudo().filtered(
            lambda num: num.digits == digits)

    def _process_leads(self, crm_lead, data, tags, comments):
        """This method calls for adding a log note in lead for configured Aircall user"""

        enable_crm_module = self.env['ir.config_parameter'].sudo().get_param(
            'cit_aircall_api_integration.enable_crm_module')

        if enable_crm_module != 'True':  # Ensure CRM module is explicitly enabled
            _logger.warning(
                "CRM module is disabled in settings. Skipping call logging "
                "in opportunities.")
            return

        manual_call_loging = self.env['ir.config_parameter'].sudo().get_param(
            'cit_aircall_api_integration.manual_call_loging'
        ) == 'True'

        partner = self._find_partner(self.env['res.partner'], data['raw_digits'])
        last_partner = partner.sorted(key=lambda p: p.id)[-1:]

        lead_to_log = None

        if len(crm_lead) == 1:
            lead_to_log = crm_lead[0]  # Log in the single opportunity

        elif len(crm_lead) > 1:
            if not manual_call_loging:
                # manual_call_loging is a string, so check for 'True'
                parent_opportunity = self.env['crm.lead'].sudo().search([
                    ('partner_id', 'in', partner.mapped('parent_id').filtered(
                        lambda p: p.active).ids)], order='id desc', limit=1)
                if parent_opportunity:
                    lead_to_log = parent_opportunity[0]
                else:
                    last_partner_lead = self.env['crm.lead'].sudo().search([
                        ('partner_id', '=', last_partner.id)
                    ], order='create_date desc', limit=1)
                    if last_partner_lead:
                        lead_to_log = last_partner_lead
                    else:
                        lead_to_log = crm_lead[0]
            else:
                # If more than one lead and manual_call_loging is False,
                # log in the one with x_add_log_note=True
                lead_with_log_note = crm_lead.filtered(lambda lead: lead.x_add_log_note)
                if lead_with_log_note:
                    lead_to_log = lead_with_log_note[0]
                    # Log in the opportunity with x_add_log_note=True

        if lead_to_log:  # Proceed only if there is a valid lead to log
            talk_time, waiting_time = self._calculate_times(data)

            if self._is_number_configured(data['number']['digits']):
                message = self._generate_message(
                    data, talk_time, waiting_time, tags, comments)
                author_ref = self.env.ref(
                    'cit_aircall_api_integration.aircall_res_partner_1',
                    raise_if_not_found=False)
                author_id = author_ref.id if author_ref else None
                if self.env['mail.message'].sudo().search_count([
                    ('aircall_call_id', '=', data['id']),
                    ('model', '=', 'crm.lead'),
                    ('res_id', '=', lead_to_log.id),
                ], limit=1):
                    return

                mail_data = lead_to_log.sudo().message_post(
                    body=message, author_id=author_id if author_id else None)
                if mail_data:
                    mail_data.aircall_call_id = data['id']
                    self.create_call_detail(
                        data['id'], data['asset'], waiting_time, lead_to_log,
                        mail_data, data, talk_time, tags, comments)

        if lead_to_log and lead_to_log.x_add_log_note:
            lead_to_log.sudo().write({
                'x_add_log_note': False
            })
