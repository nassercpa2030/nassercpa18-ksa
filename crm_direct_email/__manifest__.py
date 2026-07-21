{
    "name": "CRM Direct Email (No Follower Required)",
    "version": "18.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "Send emails directly to CRM contacts without follower requirement",
    "description": """
CRM Direct Email
================

Send emails directly to CRM opportunity contacts — no follower required.

The Problem
-----------
In standard Odoo Community, the mail composer only sends to followers of
a document. For CRM outreach this means you must first add a contact as
a follower before you can email them — an unnecessary extra step.

The Solution
------------
This module overrides the mail composer so that CRM leads automatically
include the contact partner as recipient, even when they are not a follower.

- Zero configuration needed
- Works with any mail composer action on CRM leads
- Falls back to standard behavior for non-CRM models
- No UI changes — it just works

Requirements
------------
- Odoo 18 Community or Enterprise
- CRM module installed
- Mail module installed

Support
-------
- Email: support@balane.tech
- Response within 48 business hours

Terms & Disclaimer
------------------
The author is responsible only for the original, unmodified version of this
module and its functionality within the officially supported Odoo environment.

Covered by author:
- Module installs and runs on a fresh Odoo 18 database with declared
  dependencies (crm, mail)
- No known security vulnerabilities

NOT covered:
- Compatibility with third-party or OCA modules
- Customer-specific customizations or code modifications
- Server infrastructure, performance, or database administration
    """,
    "author": "Balane Tech",
    "website": "https://balane.tech",
    "support": "support@balane.tech",
    "depends": ["crm", "mail"],
    "data": [],
    "installable": True,
    "application": False,
    "auto_install": False,
    "images": ["static/description/banner.png"],
    "license": "LGPL-3",
}
