# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class AircallMessage(models.Model):
    _name = 'aircall.message.history'
    _description = 'Aircall Message'
    _rec_name = 'digits'

    message_id = fields.Char(string='Message ID', required=True, index=True)
    body = fields.Text(string='Message Content')
    contact_name = fields.Char(string='Contact Name', default='Unknown')
    external_number = fields.Char(string='External Number', default='N/A')
    digits = fields.Char(string='Number', default='N/A')
    timestamp = fields.Char(string='Timestamp')
    status = fields.Char(string='Status')
    number_id = fields.Char(string='Number ID')
    ac_user_id = fields.Char(string='Aircall User ID')
    user_name = fields.Char(string='User Name')
    user_email = fields.Char(string='User Email')
    partner_id = fields.Many2one(
        'res.partner', string='Partner',
        help='Partner linked to the external phone number')
