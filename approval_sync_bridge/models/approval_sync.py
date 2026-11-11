
# -*- coding: utf-8 -*-

import logging
import xmlrpc.client

from odoo import api, fields, models, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


# ============================================================================
# CONNECTION SETTINGS
# ============================================================================

# SOURCE: Odoo Online
ONLINE_URL = "https://nkhremployee.odoo.com"
ONLINE_DB = "nkhremployee"
ONLINE_USER = "m.mohamed@nassercpa.com"

# Put your NEW Online API key here.
ONLINE_API_KEY = "41c3935adfcf00382953412e759a7b2c0f1693ed_oak"

# Optional: second API key, used only if the first key fails.
# Leave empty if you do not need a second key.
ONLINE_API_KEY_BACKUP = ""

# TARGET: Odoo.sh
# The module runs on this database. Do not put this value in ONLINE_DB.
TARGET_LOGIN = "m.mohamed@nassercpa.com"

BATCH_SIZE = 100


# ============================================================================
# FIELD MAPPING
# ============================================================================

REQUEST_COPY_FIELDS = (
    "name",
    "reason",
    "date",
    "reference",
    "amount",
)

APPROVER_COPY_FIELDS = (
    "required",
    "sequence",
)

APPROVER_STATE_FIELDS = (
    "status",
)

FINAL_REQUEST_STATES = {
    "approved": "approved",
    "refused": "refused",
}


# ============================================================================
# SYNC LINK MODEL
# ============================================================================

class ApprovalSyncLink(models.Model):
    _name = "approval.sync.link"
    _description = "Online / Odoo.sh Approval Link"
    _rec_name = "display_name"

    display_name = fields.Char(required=True)

    online_id = fields.Integer(
        required=True,
        index=True,
    )

    sh_id = fields.Many2one(
        "approval.request",
        required=True,
        ondelete="cascade",
        index=True,
    )

    online_write_date = fields.Datetime()
    sh_write_date = fields.Datetime()
    sh_approver_write_date = fields.Datetime()
    last_sync_date = fields.Datetime()

    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "online_request_unique",
            "unique(online_id)",
            "Online request already linked.",
        ),
        (
            "sh_request_unique",
            "unique(sh_id)",
            "Odoo.sh request already linked.",
        ),
    ]


# ============================================================================
# SYNC LOG MODEL
# ============================================================================

class ApprovalSyncLog(models.Model):
    _name = "approval.sync.log"
    _description = "Approval Synchronization Log"
    _order = "create_date desc, id desc"

    direction = fields.Selection(
        [
            ("online_to_sh", "Online to Odoo.sh"),
            ("sh_to_online", "Odoo.sh to Online"),
        ],
        required=True,
        index=True,
    )

    online_request_id = fields.Integer(index=True)
    sh_request_id = fields.Integer(index=True)
    request_name = fields.Char()

    status = fields.Selection(
        [
            ("success", "Success"),
            ("error", "Error"),
        ],
        required=True,
        default="success",
        index=True,
    )

    message = fields.Text()


# ============================================================================
# SETTINGS MODEL
# ============================================================================

class ApprovalSyncSettings(models.TransientModel):
    _inherit = "res.config.settings"

    approval_sync_online_url = fields.Char(
        string="Online URL",
        config_parameter="approval_sync_bridge.online_url",
    )

    approval_sync_online_db = fields.Char(
        string="Online Database",
        config_parameter="approval_sync_bridge.online_db",
    )

    approval_sync_online_user = fields.Char(
        string="Online API User",
        config_parameter="approval_sync_bridge.online_user",
    )

    approval_sync_online_key = fields.Char(
        string="Online API Key",
        config_parameter="approval_sync_bridge.online_api_key",
    )

    approval_sync_enabled = fields.Boolean(
        string="Enable Approval Sync",
        config_parameter="approval_sync_bridge.enabled",
    )


# ============================================================================
# APPROVAL SYNC SERVICE
# ============================================================================

class ApprovalSyncService(models.AbstractModel):
    _name = "approval.sync.service"
    _description = "Approval Synchronization Service"

    # ------------------------------------------------------------------------
    # CONFIGURATION
    # ------------------------------------------------------------------------

    @api.model
    def _p(self, key, default=False):
        return self.env["ir.config_parameter"].sudo().get_param(
            "approval_sync_bridge." + key,
            default,
        )

    # ------------------------------------------------------------------------
    # XML-RPC CONNECTION
    # ------------------------------------------------------------------------

    @api.model
    def _rpc(self):
        """
        Connect to Online using the connection constants above.

        Try ONLINE_API_KEY first.
        If it fails, try ONLINE_API_KEY_BACKUP.

        API keys are never written to logs.
        """

        url = (ONLINE_URL or "").strip().rstrip("/")
        db = (ONLINE_DB or "").strip()
        user = (ONLINE_USER or "").strip()

        if url.endswith("/odoo"):
            url = url[:-5].rstrip("/")

        if url and not url.startswith(("https://", "http://")):
            url = "https://" + url

        missing = []

        if not url:
            missing.append("ONLINE_URL")

        if not db:
            missing.append("ONLINE_DB")

        if not user:
            missing.append("ONLINE_USER")

        if missing:
            raise UserError(_(
                "Approval Sync connection settings are incomplete: %s"
            ) % ", ".join(missing))

        keys = []

        for candidate in (
            ONLINE_API_KEY,
            ONLINE_API_KEY_BACKUP,
        ):
            candidate = (candidate or "").strip()

            if (
                candidate
                and candidate != "PUT_YOUR_NEW_API_KEY_HERE"
                and candidate not in keys
            ):
                keys.append(candidate)

        if not keys:
            raise UserError(_(
                "No valid API key is configured in approval_sync.py. "
                "Set ONLINE_API_KEY to your new Online API key."
            ))

        try:
            common = xmlrpc.client.ServerProxy(
                url + "/xmlrpc/2/common",
                allow_none=True,
            )

            version = common.version()

            if not version:
                raise UserError(_(
                    "Online XML-RPC version check returned an empty response."
                ))

        except Exception as exc:
            _logger.exception(
                "Approval Sync could not contact Online XML-RPC."
            )

            raise UserError(_(
                "Could not contact Online XML-RPC service: %s"
            ) % str(exc))

        authenticated_uid = False
        authenticated_key = False

        for index, candidate_key in enumerate(keys, start=1):

            try:
                candidate_uid = common.authenticate(
                    db,
                    user,
                    candidate_key,
                    {},
                )

                if candidate_uid:
                    authenticated_uid = candidate_uid
                    authenticated_key = candidate_key

                    _logger.info(
                        "Approval Sync Online authentication succeeded "
                        "using API key candidate #%s.",
                        index,
                    )

                    break

                _logger.warning(
                    "Approval Sync API key candidate #%s was rejected.",
                    index,
                )

            except Exception:
                _logger.exception(
                    "Approval Sync authentication attempt #%s failed.",
                    index,
                )

        if not authenticated_uid:
            raise UserError(_(
                "Online authentication failed.\n\n"
                "Database: %s\n"
                "Login: %s\n\n"
                "Both configured API key candidates were rejected. "
                "Check ONLINE_API_KEY and ONLINE_API_KEY_BACKUP "
                "inside approval_sync.py."
            ) % (db, user))

        try:
            proxy = xmlrpc.client.ServerProxy(
                url + "/xmlrpc/2/object",
                allow_none=True,
            )

        except Exception as exc:
            _logger.exception(
                "Approval Sync object endpoint initialization failed."
            )

            raise UserError(_(
                "Online authentication succeeded, but the XML-RPC "
                "object endpoint could not be initialized: %s"
            ) % str(exc))

        return db, authenticated_uid, authenticated_key, proxy

    # ------------------------------------------------------------------------
    # REMOTE XML-RPC CALL
    # ------------------------------------------------------------------------

    @api.model
    def _call(
        self,
        rpc,
        db,
        uid,
        key,
        model,
        method,
        args=None,
        kwargs=None,
    ):
        return rpc.execute_kw(
            db,
            uid,
            key,
            model,
            method,
            args or [],
            kwargs or {},
        )

    # ------------------------------------------------------------------------
    # REMOTE MODEL FIELDS
    # ------------------------------------------------------------------------

    @api.model
    def _remote_fields(self, rpc, db, uid, key, model):
        try:
            result = self._call(
                rpc,
                db,
                uid,
                key,
                model,
                "fields_get",
                [],
                {
                    "attributes": [
                        "type",
                        "relation",
                        "readonly",
                        "selection",
                    ],
                },
            )

            if not isinstance(result, dict) or not result:
                raise UserError(_(
                    "The Online model '%s' returned an empty schema. "
                    "Check the Online database and installed Approvals app."
                ) % model)

            return result

        except UserError:
            raise

        except Exception as exc:

            registered = False
            diagnostic = ""

            try:
                records = self._call(
                    rpc,
                    db,
                    uid,
                    key,
                    "ir.model",
                    "search_read",
                    [[("model", "=", model)]],
                    {
                        "fields": ["model", "name"],
                        "limit": 2,
                    },
                )

                registered = bool(records)

                diagnostic = (
                    "The model is listed in ir.model but is unavailable "
                    "in the active server registry."
                    if registered
                    else
                    "The model is not registered in this connected database."
                )

            except Exception as check_exc:
                diagnostic = (
                    "Could not verify ir.model: %s" % str(check_exc)
                )

            _logger.exception(
                "Online fields_get failed for model %s on database %s",
                model,
                db,
            )

            raise UserError(_(
                "Online XML-RPC could not load model '%(model)s' "
                "from database '%(db)s'. %(diagnostic)s "
                "Original error: %(error)s"
            ) % {
                "model": model,
                "db": db,
                "diagnostic": diagnostic,
                "error": str(exc),
            })

    # ------------------------------------------------------------------------
    # CHECK REQUIRED REMOTE MODELS
    # ------------------------------------------------------------------------

    @api.model
    def _check_remote_approval_models(self, rpc, db, uid, key):

        required = (
            "approval.request",
            "approval.approver",
            "approval.category",
        )

        records = self._call(
            rpc,
            db,
            uid,
            key,
            "ir.model",
            "search_read",
            [[("model", "in", list(required))]],
            {
                "fields": ["model", "name"],
                "limit": 20,
            },
        )

        found = {
            row.get("model")
            for row in records or []
        }

        missing = [
            name
            for name in required
            if name not in found
        ]

        if missing:
            raise UserError(_(
                "The connected Online database '%s' is missing "
                "these required Approval models: %s."
            ) % (db, ", ".join(missing)))

        return True

    # ------------------------------------------------------------------------
    # TARGET USER
    # ------------------------------------------------------------------------

    @api.model
    def _target_user(self):

        user = self.env["res.users"].sudo().search(
            [
                ("login", "=", TARGET_LOGIN),
                ("active", "=", True),
            ],
            limit=1,
        )

        if not user:
            raise UserError(_(
                "Target user %s is missing or inactive in Odoo.sh."
            ) % TARGET_LOGIN)

        return user

    # ------------------------------------------------------------------------
    # LOGGING
    # ------------------------------------------------------------------------

    @api.model
    def _log(
        self,
        direction,
        status,
        message,
        online_id=False,
        sh_id=False,
        name=False,
    ):

        try:
            with self.env.cr.savepoint():

                self.env["approval.sync.log"].sudo().create({
                    "direction": direction,
                    "status": status,
                    "message": str(message)[:4000],
                    "online_request_id": online_id or False,
                    "sh_request_id": sh_id or False,
                    "request_name": name or False,
                })

        except Exception:
            _logger.exception(
                "Could not create Approval Sync log entry."
            )

    # ------------------------------------------------------------------------
    # SELECTION HELPERS
    # ------------------------------------------------------------------------

    @api.model
    def _selection_values(self, field_info):

        selection = field_info.get("selection") or []

        return {
            item[0]
            for item in selection
            if item
        }

    @api.model
    def _map_selection(
        self,
        value,
        remote_info,
        local_field,
    ):

        if value is False or value is None:
            return False

        remote_values = self._selection_values(remote_info)
        local_values = set()

        if local_field and local_field.type == "selection":

            try:
                local_values = {
                    item[0]
                    for item in local_field._description_selection(self.env)
                }

            except Exception:
                local_values = set()

        if remote_values and value not in remote_values:
            return False

        if local_values and value not in local_values:
            return False

        return value

    # ------------------------------------------------------------------------
    # REQUEST FIELD MAPPING
    # ------------------------------------------------------------------------

    @api.model
    def _request_read_fields(self, remote_fields):

        fields_to_read = [
            "id",
            "write_date",
        ]

        fields_to_read += [
            name
            for name in REQUEST_COPY_FIELDS
            if name in remote_fields
        ]

        if "category_id" in remote_fields:
            fields_to_read.append("category_id")

        if "request_status" in remote_fields:
            fields_to_read.append("request_status")

        return list(dict.fromkeys(fields_to_read))

    @api.model
    def _request_values_from_online(self, row, target_user):

        local_model = self.env["approval.request"].sudo()
        vals = {}

        for name in REQUEST_COPY_FIELDS:

            if (
                name not in row
                or name not in local_model._fields
            ):
                continue

            value = row[name]

            if value not in (False, None, ""):
                vals[name] = value

        vals["request_owner_id"] = target_user.id

        category_data = row.get("category_id")

        if (
            not category_data
            or not isinstance(category_data, (list, tuple))
        ):
            raise UserError(_(
                "Cannot import Online Approval Request #%s: "
                "the source request has no Approval Category."
            ) % row.get("id", "?"))

        category_name = (
            category_data[1]
            if len(category_data) > 1
            else ""
        )

        if not category_name:
            raise UserError(_(
                "Cannot import Online Approval Request #%s: "
                "category name is empty."
            ) % row.get("id", "?"))

        category_model = self.env["approval.category"].sudo().with_context(
            active_test=False
        )

        categories = category_model.search(
            [
                ("name", "=", category_name),
            ],
            limit=2,
        )

        if not categories:
            categories = category_model.search(
                [
                    ("name", "ilike", category_name),
                ],
                limit=2,
            )

        if not categories:
            raise UserError(_(
                "Cannot import Online Approval Request #%s: "
                "category '%s' does not exist in Odoo.sh. "
                "Create the category first."
            ) % (row.get("id", "?"), category_name))

        if len(categories) > 1:
            raise UserError(_(
                "Cannot import Online Approval Request #%s: "
                "more than one Odoo.sh category matches '%s'."
            ) % (row.get("id", "?"), category_name))

        vals["category_id"] = categories.id

        if not vals.get("category_id"):
            raise UserError(_(
                "Cannot import Online Approval Request #%s: "
                "category_id is required."
            ) % row.get("id", "?"))

        if not vals.get("name"):
            vals["name"] = _(
                "Online Approval #%s"
            ) % row.get("id", "?")

        return vals

    # ------------------------------------------------------------------------
    # REMOTE USER MAPPING
    # ------------------------------------------------------------------------

    @api.model
    def _find_local_user_by_remote_id(
        self,
        rpc,
        db,
        uid,
        key,
        remote_user_id,
    ):

        users = self._call(
            rpc,
            db,
            uid,
            key,
            "res.users",
            "read",
            [[remote_user_id]],
            {
                "fields": ["login"],
            },
        )

        if not users or not users[0].get("login"):
            return self.env["res.users"]

        return self.env["res.users"].sudo().search(
            [
                ("login", "=", users[0]["login"]),
                ("active", "=", True),
            ],
            limit=1,
        )

    # ------------------------------------------------------------------------
    # ONLINE APPROVERS -> ODOO.SH
    # ------------------------------------------------------------------------

    @api.model
    def _sync_approvers_online_to_sh(
        self,
        rpc,
        db,
        uid,
        key,
        online_request_id,
        local_request,
    ):

        remote_fields = self._remote_fields(
            rpc,
            db,
            uid,
            key,
            "approval.approver",
        )

        if not {
            "request_id",
            "user_id",
        }.issubset(remote_fields):

            _logger.warning(
                "Online approval.approver is missing request_id/user_id."
            )

            return

        wanted = [
            "id",
            "user_id",
        ]

        wanted += [
            name
            for name in APPROVER_COPY_FIELDS
            if name in remote_fields
        ]

        wanted += [
            name
            for name in APPROVER_STATE_FIELDS
            if name in remote_fields
        ]

        rows = self._call(
            rpc,
            db,
            uid,
            key,
            "approval.approver",
            "search_read",
            [[("request_id", "=", online_request_id)]],
            {
                "fields": wanted,
                "limit": 500,
                "order": "sequence asc, id asc",
            },
        )

        local_model = self.env["approval.approver"].sudo()

        for row in rows:

            if not row.get("user_id"):
                continue

            local_user = self._find_local_user_by_remote_id(
                rpc,
                db,
                uid,
                key,
                row["user_id"][0],
            )

            if not local_user:

                _logger.warning(
                    "Approver from Online user id %s was not found on SH.",
                    row["user_id"][0],
                )

                continue

            vals = {
                "request_id": local_request.id,
                "user_id": local_user.id,
            }

            for name in APPROVER_COPY_FIELDS:

                if (
                    name in row
                    and name in local_model._fields
                ):
                    vals[name] = row[name]

            for name in APPROVER_STATE_FIELDS:

                if (
                    name in row
                    and name in remote_fields
                    and name in local_model._fields
                ):

                    mapped = self._map_selection(
                        row[name],
                        remote_fields[name],
                        local_model._fields[name],
                    )

                    if mapped:
                        vals[name] = mapped

            existing = local_model.search(
                [
                    ("request_id", "=", local_request.id),
                    ("user_id", "=", local_user.id),
                ],
                limit=1,
            )

            if existing:
                # Odoo.sh remains authoritative after initial import.
                continue

            local_model.create(vals)

    # ------------------------------------------------------------------------
    # ONLINE -> ODOO.SH
    # ------------------------------------------------------------------------

    @api.model
    def _sync_online_to_sh(self):

        db, uid, key, rpc = self._rpc()

        self._check_remote_approval_models(
            rpc,
            db,
            uid,
            key,
        )

        remote_fields = self._remote_fields(
            rpc,
            db,
            uid,
            key,
            "approval.request",
        )

        wanted = self._request_read_fields(remote_fields)

        cursor_date = (
            self._p("online_cursor_date")
            or "2000-01-01 00:00:00"
        )

        cursor_id = int(
            self._p("online_cursor_id")
            or 0
        )

        domain = [
            "|",
            ("write_date", ">", cursor_date),
            "&",
            ("write_date", "=", cursor_date),
            ("id", ">", cursor_id),
        ]

        ids = self._call(
            rpc,
            db,
            uid,
            key,
            "approval.request",
            "search",
            [domain],
            {
                "order": "write_date asc, id asc",
                "limit": BATCH_SIZE,
            },
        )

        if not ids:
            return

        target_user = self._target_user()

        last_date = cursor_date
        last_id = cursor_id

        for online_id in ids:

            row_date = last_date

            try:

                with self.env.cr.savepoint():

                    rows = self._call(
                        rpc,
                        db,
                        uid,
                        key,
                        "approval.request",
                        "read",
                        [[online_id]],
                        {
                            "fields": wanted,
                        },
                    )

                    if not rows:
                        continue

                    row = rows[0]

                    row_date = (
                        row.get("write_date")
                        or cursor_date
                    )

                    link = self.env[
                        "approval.sync.link"
                    ].sudo().search(
                        [
                            ("online_id", "=", online_id),
                        ],
                        limit=1,
                    )

                    if link:

                        # Odoo.sh owns the request after first import.
                        link.write({
                            "online_write_date": row_date,
                        })

                    else:

                        vals = self._request_values_from_online(
                            row,
                            target_user,
                        )

                        request = self.env[
                            "approval.request"
                        ].sudo().create(vals)

                        self._sync_approvers_online_to_sh(
                            rpc,
                            db,
                            uid,
                            key,
                            online_id,
                            request,
                        )

                        self.env[
                            "approval.sync.link"
                        ].sudo().create({
                            "display_name": (
                                request.name
                                or "Online Approval #%s" % online_id
                            ),
                            "online_id": online_id,
                            "sh_id": request.id,
                            "online_write_date": row_date,
                            "sh_write_date": request.write_date,
                            "last_sync_date": fields.Datetime.now(),
                        })

                        self._log(
                            "online_to_sh",
                            "success",
                            "New request imported. "
                            "Odoo.sh is now authoritative.",
                            online_id,
                            request.id,
                            request.name,
                        )

                last_date = row_date
                last_id = online_id

            except Exception as exc:

                _logger.exception(
                    "Import failed for Online approval request %s",
                    online_id,
                )

                self._log(
                    "online_to_sh",
                    "error",
                    exc,
                    online_id=online_id,
                )

                break

        params = self.env["ir.config_parameter"].sudo()

        params.set_param(
            "approval_sync_bridge.online_cursor_date",
            last_date,
        )

        params.set_param(
            "approval_sync_bridge.online_cursor_id",
            last_id,
        )

    # ------------------------------------------------------------------------
    # ODOO.SH -> ONLINE USER MAPPING
    # ------------------------------------------------------------------------

    @api.model
    def _remote_user_id(
        self,
        rpc,
        db,
        uid,
        key,
        login,
    ):

        if not login:
            return False

        ids = self._call(
            rpc,
            db,
            uid,
            key,
            "res.users",
            "search",
            [[
                ("login", "=", login),
                ("active", "=", True),
            ]],
            {
                "limit": 1,
            },
        )

        return ids[0] if ids else False

    # ------------------------------------------------------------------------
    # ODOO.SH APPROVERS -> ONLINE
    # ------------------------------------------------------------------------

    @api.model
    def _sync_approvers_sh_to_online(
        self,
        rpc,
        db,
        uid,
        key,
        link,
        request,
        remote_approver_fields,
    ):

        if not {
            "request_id",
            "user_id",
        }.issubset(remote_approver_fields):
            return

        local_approvers = self.env[
            "approval.approver"
        ].sudo().search(
            [
                ("request_id", "=", request.id),
            ],
            order="sequence asc, id asc",
        )

        for approver in local_approvers:

            remote_user_id = self._remote_user_id(
                rpc,
                db,
                uid,
                key,
                approver.user_id.login,
            )

            if not remote_user_id:
                continue

            remote_ids = self._call(
                rpc,
                db,
                uid,
                key,
                "approval.approver",
                "search",
                [[
                    ("request_id", "=", link.online_id),
                    ("user_id", "=", remote_user_id),
                ]],
                {
                    "limit": 1,
                },
            )

            vals = {
                "request_id": link.online_id,
                "user_id": remote_user_id,
            }

            for name in APPROVER_COPY_FIELDS:

                if (
                    name in remote_approver_fields
                    and name in approver._fields
                ):
                    vals[name] = approver[name]

            for name in APPROVER_STATE_FIELDS:

                if (
                    name in remote_approver_fields
                    and name in approver._fields
                    and not remote_approver_fields[name].get("readonly")
                ):

                    remote_selection = self._selection_values(
                        remote_approver_fields[name]
                    )

                    value = approver[name]

                    if (
                        not remote_selection
                        or value in remote_selection
                    ):
                        vals[name] = value

            if remote_ids:

                self._call(
                    rpc,
                    db,
                    uid,
                    key,
                    "approval.approver",
                    "write",
                    [
                        [remote_ids[0]],
                        vals,
                    ],
                )

            else:

                self._call(
                    rpc,
                    db,
                    uid,
                    key,
                    "approval.approver",
                    "create",
                    [vals],
                )

    # ------------------------------------------------------------------------
    # PUSH REQUEST FIELDS TO ONLINE
    # ------------------------------------------------------------------------

    @api.model
    def _push_request_fields_to_online(
        self,
        rpc,
        db,
        uid,
        key,
        link,
        request,
        remote_fields,
    ):

        vals = {}

        for name in REQUEST_COPY_FIELDS:

            if (
                name in remote_fields
                and name in request._fields
                and not remote_fields[name].get("readonly")
            ):

                value = request[name]

                if value not in (False, None):
                    vals[name] = value

        if (
            "category_id" in remote_fields
            and request.category_id
            and not remote_fields["category_id"].get("readonly")
        ):

            remote_categories = self._call(
                rpc,
                db,
                uid,
                key,
                "approval.category",
                "search",
                [[
                    ("name", "=", request.category_id.name),
                ]],
                {
                    "limit": 1,
                },
            )

            if remote_categories:
                vals["category_id"] = remote_categories[0]

        if vals:

            self._call(
                rpc,
                db,
                uid,
                key,
                "approval.request",
                "write",
                [
                    [link.online_id],
                    vals,
                ],
            )

    # ------------------------------------------------------------------------
    # APPROVER WRITE DATE
    # ------------------------------------------------------------------------

    @api.model
    def _local_approver_write_date(self, request):

        approvers = self.env[
            "approval.approver"
        ].sudo().search(
            [
                ("request_id", "=", request.id),
            ]
        )

        dates = [
            date
            for date in approvers.mapped("write_date")
            if date
        ]

        return max(dates) if dates else False

    # ------------------------------------------------------------------------
    # ODOO.SH -> ONLINE
    # ------------------------------------------------------------------------

    @api.model
    def _push_to_online(self):

        db, uid, key, rpc = self._rpc()

        self._check_remote_approval_models(
            rpc,
            db,
            uid,
            key,
        )

        remote_request_fields = self._remote_fields(
            rpc,
            db,
            uid,
            key,
            "approval.request",
        )

        remote_approver_fields = self._remote_fields(
            rpc,
            db,
            uid,
            key,
            "approval.approver",
        )

        links = self.env[
            "approval.sync.link"
        ].sudo().search(
            [
                ("active", "=", True),
            ],
            order="id asc",
        )

        for link in links:

            try:

                with self.env.cr.savepoint():

                    request = link.sh_id.sudo()

                    if not request.exists():
                        continue

                    approver_write_date = (
                        self._local_approver_write_date(request)
                    )

                    request_changed = bool(
                        request.write_date
                        and (
                            not link.sh_write_date
                            or request.write_date > link.sh_write_date
                        )
                    )

                    approvers_changed = bool(
                        approver_write_date
                        and (
                            not link.sh_approver_write_date
                            or approver_write_date > link.sh_approver_write_date
                        )
                    )

                    if not request_changed and not approvers_changed:
                        continue

                    self._push_request_fields_to_online(
                        rpc,
                        db,
                        uid,
                        key,
                        link,
                        request,
                        remote_request_fields,
                    )

                    self._sync_approvers_sh_to_online(
                        rpc,
                        db,
                        uid,
                        key,
                        link,
                        request,
                        remote_approver_fields,
                    )

                    link.write({
                        "sh_write_date": request.write_date,
                        "sh_approver_write_date": approver_write_date,
                        "last_sync_date": fields.Datetime.now(),
                    })

                    self._log(
                        "sh_to_online",
                        "success",
                        "Odoo.sh request data and approver states "
                        "pushed to Online.",
                        link.online_id,
                        request.id,
                        request.name,
                    )

            except Exception as exc:

                _logger.exception(
                    "Export failed for approval sync link %s",
                    link.id,
                )

                self._log(
                    "sh_to_online",
                    "error",
                    exc,
                    link.online_id,
                    link.sh_id.id,
                    link.sh_id.name,
                )

    # ------------------------------------------------------------------------
    # CRON
    # ------------------------------------------------------------------------

    @api.model
    def cron_sync_approvals(self):

        enabled = str(
            self._p("enabled", "False")
        ).lower()

        if enabled not in ("true", "1", "yes"):

            _logger.info(
                "Approval Sync is disabled; cron skipped."
            )

            return True

        # Direction 1: Online -> Odoo.sh
        try:

            with self.env.cr.savepoint():
                self._sync_online_to_sh()

        except Exception as exc:

            _logger.exception(
                "Online -> Odoo.sh approval sync cycle failed."
            )

            self._log(
                "online_to_sh",
                "error",
                exc,
            )

        # Direction 2: Odoo.sh -> Online
        try:

            with self.env.cr.savepoint():
                self._push_to_online()

        except Exception as exc:

            _logger.exception(
                "Odoo.sh -> Online approval sync cycle failed."
            )

            self._log(
                "sh_to_online",
                "error",
                exc,
            )

        return True

    # ------------------------------------------------------------------------
    # TEST CONNECTION
    # ------------------------------------------------------------------------

    @api.model
    def action_test_online_connection(self):

        db, uid, key, rpc = self._rpc()

        self._check_remote_approval_models(
            rpc,
            db,
            uid,
            key,
        )

        version = self._call(
            rpc,
            db,
            uid,
            key,
            "res.users",
            "read",
            [[uid]],
            {
                "fields": [
                    "name",
                    "login",
                ],
            },
        )

        login = (
            version[0].get("login")
            if version
            else user
        ) if False else (
            version[0].get("login")
            if version
            else str(uid)
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Online connection successful"),
                "message": _("Connected to %s as %s.") % (
                    db,
                    login,
                ),
                "type": "success",
                "sticky": False,
            },
        }
