import logging
import xmlrpc.client
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
TARGET_LOGIN = "m.mohamed@nassercpa.com"
BATCH_SIZE = 100


class ApprovalSyncLink(models.Model):
    _name = "approval.sync.link"
    _description = "Online / Odoo.sh Approval Link"
    _rec_name = "display_name"

    display_name = fields.Char(required=True)
    online_id = fields.Integer(required=True, index=True)
    sh_id = fields.Many2one("approval.request", required=True, ondelete="cascade")
    online_write_date = fields.Datetime()
    sh_write_date = fields.Datetime()
    last_sync_date = fields.Datetime()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("online_request_unique", "unique(online_id)", "Online request already linked."),
        ("sh_request_unique", "unique(sh_id)", "Odoo.sh request already linked."),
    ]


class ApprovalSyncSettings(models.TransientModel):
    _inherit = "res.config.settings"

    approval_sync_online_url = fields.Char(
        string="Online URL", config_parameter="approval_sync_bridge.online_url")
    approval_sync_online_db = fields.Char(
        string="Online Database", config_parameter="approval_sync_bridge.online_db")
    approval_sync_online_user = fields.Char(
        string="Online API User", config_parameter="approval_sync_bridge.online_user")
    approval_sync_online_key = fields.Char(
        string="Online API Key", config_parameter="approval_sync_bridge.online_key")
    approval_sync_enabled = fields.Boolean(
        string="Enable Approval Sync", config_parameter="approval_sync_bridge.enabled")


class ApprovalSyncService(models.AbstractModel):
    _name = "approval.sync.service"
    _description = "Approval Synchronization Service"

    @api.model
    def _p(self, key):
        return self.env["ir.config_parameter"].sudo().get_param(
            "approval_sync_bridge." + key)

    @api.model
    def _rpc(self):
        url = (self._p("online_url") or "").rstrip("/")
        db, user, key = self._p("online_db"), self._p("online_user"), self._p("online_key")
        if not all((url, db, user, key)):
            raise UserError(_("Configure Online URL, database, API user and API key in system parameters."))
        common = xmlrpc.client.ServerProxy(url + "/xmlrpc/2/common", allow_none=True)
        uid = common.authenticate(db, user, key, {})
        if not uid:
            raise UserError(_("Online authentication failed. Check database, login and API key."))
        proxy = xmlrpc.client.ServerProxy(url + "/xmlrpc/2/object", allow_none=True)
        return db, uid, key, proxy

    @api.model
    def _call(self, rpc, db, uid, key, model, method, args=None, kwargs=None):
        return rpc.execute_kw(db, uid, key, model, method, args or [], kwargs or {})

    @api.model
    def _remote_fields(self, rpc, db, uid, key, model):
        return self._call(rpc, db, uid, key, model, "fields_get", [],
                          {"attributes": ["type", "relation", "readonly"]})

    @api.model
    def _target_user(self):
        user = self.env["res.users"].sudo().search([
            ("login", "=", TARGET_LOGIN), ("active", "=", True)], limit=1)
        if not user:
            raise UserError(_("Target user %s is missing or inactive.") % TARGET_LOGIN)
        return user

    @api.model
    def _import_approvers(self, rpc, db, uid, key, online_id, local_request):
        try:
            f = self._remote_fields(rpc, db, uid, key, "approval.approver")
            if not {"request_id", "user_id"}.issubset(f):
                return
            wanted = ["id", "user_id"] + [x for x in ("required", "sequence") if x in f]
            rows = self._call(rpc, db, uid, key, "approval.approver", "search_read",
                              [[("request_id", "=", online_id)]],
                              {"fields": wanted, "limit": 500})
            for row in rows:
                if not row.get("user_id"):
                    continue
                u = self._call(rpc, db, uid, key, "res.users", "read",
                               [[row["user_id"][0]]], {"fields": ["login"]})
                if not u:
                    continue
                local_user = self.env["res.users"].sudo().search(
                    [("login", "=", u[0].get("login"))], limit=1)
                if not local_user:
                    continue
                vals = {"request_id": local_request.id, "user_id": local_user.id}
                for name in ("required", "sequence"):
                    if name in row and name in self.env["approval.approver"]._fields:
                        vals[name] = row[name]
                existing = self.env["approval.approver"].sudo().search([
                    ("request_id", "=", local_request.id),
                    ("user_id", "=", local_user.id)], limit=1)
                if not existing:
                    self.env["approval.approver"].sudo().create(vals)
        except Exception:
            _logger.exception("Could not import approvers for Online request %s", online_id)

    @api.model
    def _sync_online_to_sh(self):
        db, uid, key, rpc = self._rpc()
        remote_fields = self._remote_fields(rpc, db, uid, key, "approval.request")
        wanted = ["id", "write_date"] + [
            x for x in ("name", "category_id", "reason", "date", "reference", "amount")
            if x in remote_fields]
        cursor = self._p("online_cursor") or "2000-01-01 00:00:00"
        since = fields.Datetime.to_string(
            fields.Datetime.from_string(cursor) - timedelta(seconds=90))
        ids = self._call(rpc, db, uid, key, "approval.request", "search",
                         [[("write_date", ">=", since)]],
                         {"order": "write_date asc, id asc", "limit": BATCH_SIZE})
        if not ids:
            return
        target = self._target_user()
        max_date = cursor
        for rid in ids:
            try:
                data = self._call(rpc, db, uid, key, "approval.request", "read",
                                  [[rid]], {"fields": wanted})
                if not data:
                    continue
                row = data[0]
                max_date = max(max_date, row.get("write_date") or cursor)
                link = self.env["approval.sync.link"].sudo().search(
                    [("online_id", "=", rid)], limit=1)
                if link:
                    # Online cannot overwrite an existing SH request or its workflow.
                    link.write({"online_write_date": row.get("write_date")})
                    continue
                vals = {}
                for name in ("name", "reason", "date", "reference", "amount"):
                    if name in row and name in self.env["approval.request"]._fields:
                        vals[name] = row[name]
                vals["request_owner_id"] = target.id
                if row.get("category_id"):
                    category = self.env["approval.category"].sudo().search(
                        [("name", "=", row["category_id"][1])], limit=1)
                    if category:
                        vals["category_id"] = category.id
                if not vals.get("name"):
                    vals["name"] = "Online Approval #%s" % rid
                request = self.env["approval.request"].sudo().create(vals)
                self.env["approval.sync.link"].sudo().create({
                    "display_name": request.name, "online_id": rid, "sh_id": request.id,
                    "online_write_date": row.get("write_date"),
                    "sh_write_date": request.write_date,
                    "last_sync_date": fields.Datetime.now(),
                })
                self._import_approvers(rpc, db, uid, key, rid, request)
                self.env["approval.sync.log"].sudo().create({
                    "direction": "online_to_sh", "online_request_id": rid,
                    "sh_request_id": request.id, "request_name": request.name,
                    "status": "success", "message": "Request imported; matching approvers imported where possible.",
                })
            except Exception as exc:
                _logger.exception("Import failed for Online request %s", rid)
                self.env["approval.sync.log"].sudo().create({
                    "direction": "online_to_sh", "online_request_id": rid,
                    "status": "error", "message": str(exc)})
        self.env["ir.config_parameter"].sudo().set_param(
            "approval_sync_bridge.online_cursor", max_date)

    @api.model
    def _push_to_online(self):
        db, uid, key, rpc = self._rpc()
        remote_fields = self._remote_fields(rpc, db, uid, key, "approval.request")
        links = self.env["approval.sync.link"].sudo().search([("active", "=", True)])
        for link in links:
            try:
                req = link.sh_id.sudo()
                if link.sh_write_date and req.write_date <= link.sh_write_date:
                    continue
                vals = {}
                for name in ("name", "reason", "date", "reference", "amount"):
                    if name in remote_fields and name in req._fields and req[name] is not False:
                        vals[name] = req[name]
                if "category_id" in remote_fields and req.category_id:
                    cats = self._call(rpc, db, uid, key, "approval.category", "search",
                                      [[("name", "=", req.category_id.name)]], {"limit": 1})
                    if cats:
                        vals["category_id"] = cats[0]
                if vals:
                    self._call(rpc, db, uid, key, "approval.request", "write",
                               [[link.online_id], vals])

                # Mirror approver membership by matching user login.
                af = self._remote_fields(rpc, db, uid, key, "approval.approver")
                if {"request_id", "user_id"}.issubset(af):
                    local_approvers = self.env["approval.approver"].sudo().search(
                        [("request_id", "=", req.id)])
                    for approver in local_approvers:
                        remote_users = self._call(
                            rpc, db, uid, key, "res.users", "search",
                            [[("login", "=", approver.user_id.login)]], {"limit": 1})
                        if not remote_users:
                            continue
                        exists = self._call(
                            rpc, db, uid, key, "approval.approver", "search",
                            [[("request_id", "=", link.online_id),
                              ("user_id", "=", remote_users[0])]], {"limit": 1})
                        av = {"request_id": link.online_id, "user_id": remote_users[0]}
                        for fname in ("required", "sequence"):
                            if fname in af and fname in approver._fields:
                                av[fname] = approver[fname]
                        if exists:
                            self._call(rpc, db, uid, key, "approval.approver", "write",
                                       [[exists[0], av]])
                        else:
                            self._call(rpc, db, uid, key, "approval.approver", "create", [av])

                # Public actions are attempted only when the local request is final.
                state = req.request_status if "request_status" in req._fields else False
                action = {"approved": "action_approve", "refused": "action_refuse"}.get(state)
                if action:
                    try:
                        self._call(rpc, db, uid, key, "approval.request", action,
                                   [[link.online_id]])
                    except Exception:
                        _logger.warning("Could not mirror %s for Online request %s",
                                        state, link.online_id, exc_info=True)

                link.write({"sh_write_date": req.write_date,
                            "last_sync_date": fields.Datetime.now()})
                self.env["approval.sync.log"].sudo().create({
                    "direction": "sh_to_online", "online_request_id": link.online_id,
                    "sh_request_id": req.id, "request_name": req.name,
                    "status": "success", "message": "Odoo.sh changes pushed to Online."})
            except Exception as exc:
                _logger.exception("Export failed for link %s", link.id)
                self.env["approval.sync.log"].sudo().create({
                    "direction": "sh_to_online", "online_request_id": link.online_id,
                    "sh_request_id": link.sh_id.id, "request_name": link.sh_id.name,
                    "status": "error", "message": str(exc)})

    @api.model
    def cron_sync_approvals(self):
        if self._p("enabled") not in ("True", "true", "1"):
            return
        try:
            self._sync_online_to_sh()
        except Exception as exc:
            _logger.exception("Online to SH sync cycle failed")
            self.env["approval.sync.log"].sudo().create({
                "direction": "online_to_sh", "status": "error", "message": str(exc)})
        try:
            self._push_to_online()
        except Exception as exc:
            _logger.exception("SH to Online sync cycle failed")
            self.env["approval.sync.log"].sudo().create({
                "direction": "sh_to_online", "status": "error", "message": str(exc)})
