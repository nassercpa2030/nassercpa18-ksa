# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

import ast
import re
import logging
from odoo import fields, models, api
from datetime import datetime

_logger = logging.getLogger(__name__)


class AircallDetails(models.Model):
    _name = 'aircall.details'
    _description = 'Aircall Connection'
    _rec_name = 'customer_id'

    call_by_user = fields.Char(string='By User')
    recording_url = fields.Char(string='Recording')
    customer_id = fields.Many2one('res.partner', string='Contact Name')
    phonenumbers = fields.Char(string='Phone Number')
    call_qualification = fields.Char(string='Call Type')
    call_duration = fields.Char(string='Call Duration')
    waiting_time = fields.Char(string='Waiting Time')
    call_time = fields.Char(string='Call Time')
    air_call_number = fields.Char(string='Aircall number')
    tags = fields.Char(string='Tags')
    notes = fields.Char(string='Notes')
    sentiments = fields.Char(string='Mood')
    key_topics = fields.Char(string='Key Topics')
    key_topics_display = fields.Html(
        compute='_compute_key_topics_display', store=False)
    aircall_call_id = fields.Char(string='Air Call Log ID')
    aircall_summary = fields.Char(
        string='Summary By Air Call', translate=True,
        default='No Summary Available For this Call')
    aircall_transcription = fields.Char(
        string='Transcription By Air Call', translate=True)
    aircall_transcription_display = fields.Html(
        string='Formatted Transcription', compute='_compute_transcription_display')
    enable_summary = fields.Boolean(
        string='Enable Summary', compute='_compute_settings_fields', store=False)
    enable_transcription = fields.Boolean(
        string='Enable Transcription', compute='_compute_settings_fields', store=False)

    @api.depends('key_topics')
    def _compute_key_topics_display(self):
        for rec in self:
            if rec.key_topics and rec.key_topics.startswith('['):
                topics_list = ast.literal_eval(rec.key_topics)
                rec.key_topics_display = ' '.join([
                    f'''<span class="badge rounded-pill border me-1 mb-1 text-dark"
                            style="background-color:#0e858a; color: white !important; border-color:#A3CAAA; padding:8px 14px; font-size:13px;">
                            {tag}
                        </span>'''
                    for tag in topics_list
                ])
            else:
                rec.key_topics_display = 'No Key Topics to Display'

    def _compute_settings_fields(self):
        config_param = self.env['ir.config_parameter']
        for record in self:
            record.enable_summary = config_param.sudo().get_param(
                'cit_aircall_api_integration.enable_summary_feature', default=False)
            record.enable_transcription = config_param.sudo().get_param(
                'cit_aircall_api_integration.enable_transcription_feature', default=False)

    @api.depends('aircall_transcription')
    def _compute_transcription_display(self):
        for record in self:
            if record.call_time:
                try:
                    time_str = record.call_time or "0"
                    try:
                        time_obj = datetime.strptime(time_str, "%H:%M:%S")
                        total_seconds = time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second
                    except ValueError:
                        # Handle non-standard or invalid time formats
                        # _logger.warning(f"Invalid time format for call_time: {time_str}")
                        total_seconds = 0

                    # _logger.info(
                    #     f"Parsed '{self.call_time}' into {total_seconds} seconds.")

                    if total_seconds < 20:
                        record.aircall_transcription_display = '''
                            <div>
                                <p><strong>We can’t transcribe due to the duration of the call</strong></p>
                                <p>Sorry, we can only transcribe calls that last a certain amount of time.</p>
                            </div>
                        '''
                        continue
                except (ValueError, TypeError):
                    # Handle invalid call_time format
                    record.aircall_transcription_display = '''
                        <div>
                            <p><strong>Unable to process call duration</strong></p>
                            <p>The call duration format is invalid.</p>
                        </div>
                    '''
                    continue
            if not record.aircall_transcription:
                html_content = '''
                            <div class="p-4 text-center" style="
                                font-family: 'Segoe UI', Tahoma, sans-serif;
                                background: #fff;
                                border-radius: 12px;
                                border: 1px solid #e0e0e0;
                                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                                color: #555;">
                                <p style="font-size: 16px;font-weight: 500;margin-bottom: 10px;">No Transcription Available</p>
                                <p style="font-size: 14px;color: #777;">There is no transcription data for this call.</p>
                            </div>
                        '''
                record.aircall_transcription_display = html_content
                continue
            try:
                transcription_data = ast.literal_eval(record.aircall_transcription)
            except (ValueError, SyntaxError):
                record.aircall_transcription_display = '<p>No valid transcription data available.</p>'
                continue

            customer_name = record.customer_id.name if record.customer_id else 'Customer'

            # Define a color palette and speaker map
            color_palette = [
                '#007bff', '#28a745', '#17a2b8', '#ffc107',
                '#6f42c1', '#fd7e14', '#20c997', '#dc3545'
            ]
            speaker_colors = {}
            color_index = 0

            html_content = '''
                    <div class=" " style="
                        font-family: 'Segoe UI', Tahoma, sans-serif;
                        padding: 20px;
                        background: #fff;
                        border-radius: 12px;
                        border: 1px solid #e0e0e0;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                        position: relative;
                    ">
                '''
            if transcription_data:
                for entry in transcription_data:
                    time_range = entry.get('time_range', 'N/A')
                    speaker_raw = entry.get('speaker', '')
                    text = entry.get('text', '')

                    if 'Internal' in speaker_raw:
                        speaker_id = 'You'
                    elif 'External' in speaker_raw:
                        match = re.search(r'\+\d+', speaker_raw)
                        if match:
                            phone = match.group()
                            partner = record.env['res.partner'].search([
                                ('phone_mobile_search', 'ilike', phone)
                            ], limit=1)
                            partner_name = partner.name if partner else f'Customer {phone}'
                            speaker_id = partner_name
                        else:
                            speaker_id = customer_name or 'User'

                    # Assign color if new speaker
                    if speaker_id not in speaker_colors:
                        speaker_colors[speaker_id] = color_palette[color_index % len(
                            color_palette)]
                        color_index += 1

                    color = speaker_colors[speaker_id]

                    html_content += f'''
                        <div class="ps-5 mb-3" style="
                            display: flex;
                            align-items: flex-start;
                            position: relative;
                        ">
                            <div style="
                                position: absolute;
                                left: 0;
                                top: 6px;
                                width: 8px;
                                height: 8px;
                                background-color: {color};
                                border-radius: 50%;
                            "></div>
                            <div style="
                                position: absolute;
                                left: 3px;
                                top: 20px;
                                width: 2px;
                                height: calc(100% - 20px);
                                background-color: #d0d7e3;
                            "></div>
                            <div>
                                <div style="font-size: 14px; color: #333; margin-bottom: 4px;">
                                    <strong style="color: {color};">{time_range}</strong> — 
                                    <span style="color:#555;font-style:italic;">{speaker_id}</span>
                                </div>
                                <div class="px-4 py-3" style="
                                    font-size: 15px;
                                    color: #222;
                                    line-height: 1.5;
                                    background: #fff;
                                    border-radius: 8px;
                                    border: 2px solid {color};
                                ">
                                    {text}
                                </div>
                            </div>
                        </div>
                    '''
                html_content += '</div>'
                record.aircall_transcription_display = html_content
            else:
                html_content = '''
                            <div class="p-4 text-center" style="
                                font-family: 'Segoe UI', Tahoma, sans-serif;
                                background: #fff;
                                border-radius: 12px;
                                border: 1px solid #e0e0e0;
                                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                                color: #555;">
                                <p style="font-size: 16px;font-weight: 500;margin-bottom: 10px;">No Transcription Available</p>
                                <p style="font-size: 14px;color: #777;">There is no transcription data for this call.</p>
                            </div>
                        '''
                record.aircall_transcription_display = html_content
