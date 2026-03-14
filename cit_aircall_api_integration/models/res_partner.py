# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

import logging
from odoo.exceptions import ValidationError, UserError
from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)

try:
    import phonenumbers
except Exception as e:
    # _logger.error(f"Import error: %s {e}")
    raise ValidationError("phonenumbers Import error")


class ResPartner(models.Model):
    _inherit = 'res.partner'

    phone = fields.Char(unaccent=False, copy=False)
    email = fields.Char(copy=False)
    synced_to_aircall = fields.Boolean(string='Synced to Aircall', copy=False)
    last_name = fields.Char(string='Last Name')
    aircall_id = fields.Char(string='Aircall ID', copy=False)
    direct_link = fields.Char(string='Direct Link', copy=False)
    is_shared = fields.Boolean(string='Is Shared', copy=False)
    from_register_contact = fields.Boolean(string='From Register Contact', copy=False)
    updated_contact = fields.Boolean(string='Updated Contact', copy=False)
    phone_details_ids = fields.One2many(
        'phone.details', 'partner_id', string='Phone Details',
        copy=False, help='Phone Number Details When new contact create for Aircall')
    email_details_ids = fields.One2many(
        'email.details', 'partner_id', string='Email Details',
        copy=False, help='New Email ID when new contact create for Aircall')
    aircall_detail_ids = fields.One2many(
        'aircall.details', 'customer_id', string='Air Call')
    x_add_log_note = fields.Boolean(string='Add Log Note', default=False)
    aircall_message_ids = fields.One2many(
        'aircall.message.history', 'partner_id', string='Aircall Messages')
    fail_to_sync = fields.Boolean(string='Fail to sync', default=False)
    is_phone_formated = fields.Boolean(string='Is phone formated', default=False)

    def write(self, vals):
        if any(field in vals for field in ['name', 'phone', 'email', 'mobile']):
            vals['updated_contact'] = False

        phone_format_enabled = self.env['ir.config_parameter'].sudo().get_param(
            'cit_aircall_api_integration.default_phone_formate', 'False'
        ) == 'True'

        if phone_format_enabled:
            if 'phone' in vals and vals['phone']:
                vals['phone'] = self._format_phone_number(vals['phone'])
            if 'mobile' in vals and vals['mobile']:
                vals['mobile'] = self._format_phone_number(vals['mobile'])

        return super(ResPartner, self).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        phone_format_enabled = self.env['ir.config_parameter'].sudo().get_param(
            'cit_aircall_api_integration.default_phone_formate', 'False'
        ) == 'True'

        for vals in vals_list:
            if phone_format_enabled:
                if 'phone' in vals and vals['phone']:
                    vals['phone'] = self._format_phone_number(vals['phone'])
                if 'mobile' in vals and vals['mobile']:
                    vals['mobile'] = self._format_phone_number(vals['mobile'])

        return super(ResPartner, self).create(vals_list)

    def _format_phone_number(self, number):
        """Helper method to format the phone number to international format."""
        try:
            return phonenumbers.format_number(
                phonenumbers.parse(number),
                phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
        except phonenumbers.NumberParseException:
            raise ValidationError(
                'Phone number must have correct value, country code, or region.')
        except Exception as e:
            raise ValidationError(
                'An unexpected error occurred while formatting the phone number.')

    def try_again_to_sync(self):
        try_again_sync = self.env['ir.config_parameter'].sudo().get_param(
            'cit_aircall_api_integration.enable_try_again_syncing')
        if try_again_sync:
            # False the 'fail_to_sync' field for sync the record again to aircall
            self.write({'fail_to_sync': False})
            self.env['aircall.connection'].post_contacts(partner_ids=self.ids)
        else:
            # throw the error if related option not enabled in aircall configuration
            raise UserError(_(
                "Please enable the 'Manually try again to sync the fail contact?' "
                "option from Aircall configuration setting."))

    @api.model
    def _cron_format_partner_phone(self):
        partners = self.search([
            ('is_phone_formated', '=', False),
            ('phone', '!=', False),
        ], limit=200)

        for partner in partners:
            phone = partner.phone.strip()
            clean_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
            if not clean_phone.startswith('+'):
                continue

            try:
                parsed_number = phonenumbers.parse(clean_phone, None)
                if not phonenumbers.is_valid_number(parsed_number):
                    continue

                formatted_phone = phonenumbers.format_number(
                    parsed_number,
                    phonenumbers.PhoneNumberFormat.INTERNATIONAL
                )

                partner.write({
                    'phone': formatted_phone,
                    'is_phone_formated': True,
                })

            except Exception:
                continue
