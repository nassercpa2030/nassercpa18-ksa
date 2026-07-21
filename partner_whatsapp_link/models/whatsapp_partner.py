# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    whatsapp_url = fields.Html(compute='_set_whatsapp_url')

    def _set_whatsapp_url(self):
        for obj in self:
            url = ''
            if obj.mobile:
                url = """
                <a target="_blank" href="https://api.whatsapp.com/send?phone=%s">
                    <i class="fa fa-whatsapp" style="font-size: 30px;"/> <span class="hidden-lg hidden-xl">Send via WhatsApp</span>
                </a>
                """ % obj.mobile
            obj.whatsapp_url = url
