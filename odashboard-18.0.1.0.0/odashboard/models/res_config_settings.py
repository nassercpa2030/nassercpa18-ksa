# -*- coding: utf-8 -*-
import uuid
import logging
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from ..hooks import post_init_hook

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    odashboard_plan = fields.Char(string='Odashboard Plan', config_parameter="odashboard.plan")
    odashboard_key = fields.Char(string="Odashboard Key", config_parameter="odashboard.key")
    odashboard_key_synchronized = fields.Boolean(string="Key Synchronized",
                                                 config_parameter="odashboard.key_synchronized", readonly=True)
    odashboard_uuid = fields.Char(string="Odashboard UUID", config_parameter="odashboard.uuid", readonly=True)
    odashboard_is_free_trial = fields.Boolean(string="Is Free Trial",
                                              config_parameter="odashboard.is_free_trial", readonly=True)
    odashboard_free_trial_end_date = fields.Char(string="License Valid Until",
                                                config_parameter="odashboard.free_trial_end_date", readonly=True)

    def get_my_key(self):
        """Generate internal 10-year license and refresh view"""
        post_init_hook(self.env)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def synchronize_key(self):
        """Local synchronize: just mark as synchronized"""
        post_init_hook(self.env)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def desynchronize_key(self):
        """Desynchronize key locally"""
        config_params = self.env['ir.config_parameter'].sudo()
        config_params.set_param('odashboard.key_synchronized', False)
        config_params.set_param('odashboard.key', '')
        config_params.set_param('odashboard.plan', '')
        config_params.set_param('odashboard.is_free_trial', False)
        config_params.set_param('odashboard.free_trial_end_date', '')
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
