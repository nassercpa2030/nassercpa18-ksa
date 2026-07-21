# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

import base64
import json
from odoo.tools import frozendict
from odoo import api, models


class BaseOverride(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def web_search_read(
            self, domain, specification, offset=0, limit=None, order=None,
            count_limit=None):
        if 'params' in self.env.context and 'aircall_domain' in self.env.context.get(
                'params'):
            aircall_domain = self.env.context['params']['aircall_domain']
            if aircall_domain:
                missing_padding = len(aircall_domain) % 4
                if missing_padding:
                    aircall_domain += '=' * (4 - missing_padding)
                aircall_domain = base64.urlsafe_b64decode(aircall_domain).decode()
                domain = domain + json.loads(aircall_domain)

        res = super().web_search_read(
            domain=domain, specification=specification, offset=offset, limit=limit,
            order=order, count_limit=count_limit)
        return res

    def onchange(self, values, field_names, fields_spec):
        if 'params' in self.env.context and 'context' in self.env.context.get('params'):
            context_str = self.env.context['params'].get('context')
            context_dict = json.loads(context_str)
            # Merge the new context into the current context
            context = dict(self.env.context, **context_dict)
            self.env.context = frozendict(context)
        return super(BaseOverride, self).onchange(values, field_names, fields_spec)
