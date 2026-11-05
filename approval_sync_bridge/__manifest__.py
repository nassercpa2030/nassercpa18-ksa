{
    "name": "Approval Sync Bridge",
    "version": "18.0.1.0.0",
    "category": "Human Resources/Approvals",
    "summary": "Synchronize approval requests between Odoo Online and Odoo.sh",
    "depends": ["approvals", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/approval_sync_views.xml"
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3"
}
