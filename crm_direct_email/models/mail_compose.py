import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    def _get_partner_ids(self):
        """
        Override to ensure CRM leads can send direct emails to contacts
        without requiring them to be followers.

        Standard Odoo behavior: Emails are only sent to followers
        This override: If no partners found and we're on a CRM lead,
        automatically include the lead's contact partner.
        """
        partners = super()._get_partner_ids()

        # Only extend behavior for CRM leads when no partners found
        if not partners and self.model == "crm.lead" and self.res_id:
            try:
                lead = self.env["crm.lead"].browse(self.res_id)
                if lead.exists() and lead.partner_id and lead.partner_id.email:
                    _logger.debug(
                        "CRM Direct Email: Adding partner %s for lead %s",
                        lead.partner_id.id, lead.id
                    )
                    return lead.partner_id
            except Exception as e:
                _logger.warning(
                    "CRM Direct Email: Failed to get partner for lead %s: %s",
                    self.res_id, e
                )

        return partners
