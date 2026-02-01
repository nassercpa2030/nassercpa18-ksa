# -*- coding: utf-8 -*-
import uuid
import logging
from datetime import datetime, timedelta
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def post_init_hook(env):
    """Create internal Odashboard license valid for 10 years"""
    try:
        env = api.Environment(env.cr, SUPERUSER_ID, {})
        config = env['ir.config_parameter'].sudo()

        # Database UUID
        db_uuid = config.get_param('odashboard.uuid')
        if not db_uuid:
            db_uuid = str(uuid.uuid4())
            config.set_param('odashboard.uuid', db_uuid)

        # License Key
        license_key = str(uuid.uuid4())

        # Expiration date: 10 سنوات
        end_date = (datetime.now() + timedelta(days=3650)).strftime('%Y-%m-%d')

        # Store license data
        config.set_param('odashboard.key', license_key)
        config.set_param('odashboard.plan', 'premium')
        config.set_param('odashboard.license_type', 'internal')
        config.set_param('odashboard.start_date', datetime.now().strftime('%Y-%m-%d'))
        config.set_param('odashboard.end_date', end_date)
        config.set_param('odashboard.is_active', True)
        config.set_param('odashboard.key_synchronized', True)
        config.set_param('odashboard.is_free_trial', False)
        config.set_param('odashboard.free_trial_end_date', end_date)

        _logger.info("Internal Odashboard license created | Key: %s | Valid until: %s | DB: %s",
                     license_key, end_date, db_uuid)

    except Exception as e:
        _logger.exception("Failed to create 10-year license: %s", e)

def uninstall_hook(env):
    """Cleanup license data on uninstall"""
    try:
        env = api.Environment(env.cr, SUPERUSER_ID, {})
        config = env['ir.config_parameter'].sudo()

        keys = [
            'odashboard.key', 'odashboard.plan', 'odashboard.uuid',
            'odashboard.license_type', 'odashboard.start_date', 'odashboard.end_date',
            'odashboard.is_active', 'odashboard.key_synchronized',
            'odashboard.is_free_trial', 'odashboard.free_trial_end_date'
        ]
        config.search([('key', 'in', keys)]).unlink()
        _logger.info("ODashboard license data removed successfully")
    except Exception as e:
        _logger.exception("License cleanup failed: %s", e)
