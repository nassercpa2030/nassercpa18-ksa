# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

import logging
from odoo.addons.cit_aircall_api_integration.models.authorization import AuthorizeAircallApi
from odoo import models

_logger = logging.getLogger(__name__)


class AircallConnection(models.Model):
    _name = 'aircall.connection'
    _description = 'Aircall Connection'

    def get_contact_values(self, partner):
        """Used to get contact value."""
        phone = partner.phone.strip(' \xa0') if partner.phone else False
        mobile = partner.mobile.strip(' \xa0') if partner.mobile else False
        value = {
            'first_name': partner.name,
            'last_name': partner.last_name or '',
            'company_name': partner.parent_name or '',
            'information': 'external_custom_id:%s' % (partner.id),
            'phone_numbers': []
        }
        if partner.phone:
            value['phone_numbers'].append({
                'label': 'Work',
                'value': phone
            })
        if partner.mobile:
            value['phone_numbers'].append({
                'label': 'Mobile',
                'value': mobile,
            })
        return value

    def get_aircall_auth(self):
        """Used to get authentication values."""
        get_param = self.env['ir.config_parameter'].sudo().get_param
        url = get_param(
            'cit_aircall_api_integration.default_api_url',
            default='https://api.aircall.io')
        api_id = get_param('cit_aircall_api_integration.default_api_id', default='dummy')
        api_token = get_param(
            'cit_aircall_api_integration.default_api_token', default='dummy')
        auth = False
        if get_param('cit_aircall_api_integration.aircall_auth', default=True):
            auth = AuthorizeAircallApi(url, api_id, api_token).get_authentication()
        return auth, url, api_id, api_token

    def update_partner_aircall(
            self, limit, try_again_sync, partner_ids, phone_code_lst,
            url, api_id, api_token):
        """Used to Update Partner In Aircall."""
        domain = [
            ('synced_to_aircall', '=', True),
            ('aircall_id', '!=', False),
            ('updated_contact', '=', False)
        ]

        if partner_ids:
            domain += [('id', 'in', partner_ids)]
        elif try_again_sync:
            domain += [('fail_to_sync', '=', False)]

        update_partner = self.env['res.partner'].sudo().search(domain, order='id desc')
        valid_partners = list(
                set([partner for partner in update_partner for code in phone_code_lst if
                     code and (code in partner.phone if partner.phone else False) or (
                         code in partner.mobile if partner.mobile else False)]))[:limit]

        for i, partner in enumerate(valid_partners):
            # _logger.info('\n\nContact count%s', i)
            contacts = AuthorizeAircallApi(url, api_id, api_token).post_contacts(
                self.get_contact_values(partner))
            # _logger.info(contacts.json())
            if contacts and contacts.json():
                partner.updated_contact = True
                partner.message_post(body='Contact is Updated to Aircall successfully.')
            else:
                partner.message_post(
                    body='Contact is not Updated to the Aircall due to this error, %s' % (
                        contacts.json().get('troubleshoot')))
                if try_again_sync:
                    # when contact syncing failed then update this field for
                    # manually sync operation.
                    partner.fail_to_sync = True
        return True

    def post_contacts(self, limit=55, partner_ids=None):
        """Used to post contact from odoo to aircall. """
        auth, url, api_id, api_token = self.get_aircall_auth()
        if auth and auth.json():
            # filter partner based on valid domain,
            # email and with valid country phoneCode phone.
            country_obj = self.env['res.country']
            phone_code_lst = ['+' + str(phone_code) for phone_code in
                              country_obj.search([], order='phone_code').mapped(
                                  'phone_code')]

            try_again_sync = self.env['ir.config_parameter'].sudo().get_param(
                'cit_aircall_api_integration.enable_try_again_syncing')
            self.update_partner_aircall(
                limit, try_again_sync, partner_ids, phone_code_lst, url,
                api_id, api_token)

            domain = [
                '&',
                ('synced_to_aircall', '=', False),
                ('aircall_id', '=', False),
                '|',
                ('phone', '!=', ''),
                ('mobile', '!=', '')
            ]
            if partner_ids:
                # when user manually try again to sync the fail contacts
                # then we will sync only that selected contact.
                domain = ['&', ('id', 'in', partner_ids)] + domain
            elif try_again_sync:
                # enable_try_again_syncing is enabled then we will find the
                # fail contact for sync to airall.
                domain = ['&', ('fail_to_sync', '=', False)] + domain

            partners = self.env['res.partner'].sudo().search(domain, order='id desc')
            valid_partners = list(set([
                    partner for partner in partners
                    for code in phone_code_lst
                    if (partner.phone and code in partner.phone) or (partner.mobile and code in partner.mobile)
                ]))[:limit]

            # _logger.info('ValidPartner to be posted on Aircall: %s - %s', len(
            #     valid_partners), valid_partners)

            for i, partner in enumerate(valid_partners):
                _logger.info('\n\nContact count %s', i)
                contacts = AuthorizeAircallApi(url, api_id, api_token).post_contacts(
                    self.get_contact_values(partner))
                # _logger.info(contacts.json())
                if contacts and contacts.json():
                    partner.update({
                        'aircall_id': contacts.json()['contact']['id'],
                        'synced_to_aircall': True,
                        'updated_contact': True,
                    })
                    partner.message_post(
                        body='Contact is synced to Aircall successfully.')
                else:
                    partner.message_post(
                        body='Contact is not synced to the Aircall due to '
                             'this error, %s' % (contacts.json().get('troubleshoot')))
                    if try_again_sync:
                        # when contact syncing failed then update this field for
                        # manually sync operation.
                        partner.fail_to_sync = True
