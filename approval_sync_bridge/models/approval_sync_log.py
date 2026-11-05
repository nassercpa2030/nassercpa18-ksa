from odoo import fields, models


class ApprovalSyncLog(models.Model):
    _name = "approval.sync.log"
    _description = "Approval Synchronization Log"
    _order = "create_date desc, id desc"

    direction = fields.Selection([
        ("online_to_sh", "Online to Odoo.sh"),
        ("sh_to_online", "Odoo.sh to Online"),
    ], required=True)
    online_request_id = fields.Integer()
    sh_request_id = fields.Integer()
    request_name = fields.Char()
    status = fields.Selection([
        ("success", "Success"), ("error", "Error"), ("skipped", "Skipped")
    ], required=True, default="success")
    message = fields.Text()
