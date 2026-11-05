APPROVAL SYNC BRIDGE - ODOO 18

INSTALL
1. Copy this folder into your custom addons repository on branch staging/18.0.
2. Commit/push, update Apps List, install Approval Sync Bridge.
3. Configure system parameters:
   approval_sync_bridge.online_url = https://nasser-employees-approvals.odoo.com
   approval_sync_bridge.online_db = actual Online database name
   approval_sync_bridge.online_user = dedicated Online API login
   approval_sync_bridge.online_key = Online API key
   approval_sync_bridge.enabled = True

Target SH user is configured in code:
m.mohamed@nassercpa.com

The module creates a Scheduled Action configured for one minute. Odoo.sh
execution is best-effort and may be delayed; one minute is not guaranteed.

IMPORTANT LIMITATIONS
- This is a starter integration and MUST be tested on staging before real use.
- Imports standard request fields and matching approver membership.
- Category mapping requires identical category names in both databases.
- The designated SH user becomes request_owner_id.
- Arbitrary category-specific fields, attachments, chatter, product lines and
  custom fields are not transferred by this starter version.
- The return workflow calls public action_approve/action_refuse methods if
  available. Approval workflow implementations can differ between databases.
- It intentionally does not import changed Online data over an already-linked
  SH request. SH remains authoritative.
- Confirm Online API access is included in the subscription. Use an API key,
  not the user's normal password. Never commit secrets to Git.
