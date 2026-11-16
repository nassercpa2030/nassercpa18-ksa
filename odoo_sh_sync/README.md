# Odoo.sh HR & Approvals Sync

Odoo 18 module for controlled one-way import from an Online Odoo database into this Odoo.sh database.

## Supported inbound models

The inbound direction is intentionally restricted to:
- `hr.department`
- `hr.job`
- `hr.employee`
- `approval.request` (actual requests created by employees)
- `approval.approver` (approval lines/users)

Both databases must have the HR and Approvals applications installed, with compatible versions and matching custom fields/modules.

## Setup on Odoo.sh

1. Install/upgrade this module on Odoo.sh.
2. Open **Settings → Odoo.sh Sync → Sync Configurations**.
3. Enter the Online database URL, database name, integration username, and password/API password.
4. Set **Sync Direction** to **Online → Odoo.sh**.
5. Keep **Online Models to Import** limited to the listed HR/Approvals models.
6. Test the connection and run **Sync Now** once on a staging database for the initial backfill.
7. Upgrade the module so its scheduled job is installed; it polls Online every minute and imports new/changed employee records, approval requests, and approver lines automatically.
8. Review **Sync History** and validate the imported employee-created requests and approver lines.

## Important behavior

- The importer stores a separate Online-ID → Odoo.sh-ID mapping; it does not assume IDs are equal.
- Existing mapped records are updated; unmapped records are created.
- It imports stored fields shared by both databases, skips computed/related fields, attachment relations, binary/image fields, and one2many fields. It maps users and employees by configured mapping, login, email, and unique name where possible.
- Approval categories are reference data only: they are not imported as a separate synchronization stream. The importer matches by name and creates a missing local category when needed to satisfy an actual approval request.
- Existing approval requests are backfilled even when a previous run partially failed; ID mappings prevent duplicates.
- It deliberately does not import unrelated sales, accounting, stock, POS, or general business models.
- The sync watermark is not advanced when record errors occur, so failed records are retried on the next run. The scheduled job runs every minute; this is near-real-time polling, not an instant Online webhook.
- This is a one-way importer. Changes made on Odoo.sh are not sent back to Online.
- Deletions are not propagated.
- Run on staging first. Custom approval workflows, custom required fields, record rules, company configuration, employee users, and custom fields can require additional mapping or adaptation. Use a dedicated integration user with the necessary read access on Online and create/write access on Odoo.sh.

## Connection

The fields shown as **Online Source** refer to the Online database from which records are pulled. This module must be installed on the destination Odoo.sh database.


## Online to Odoo.sh: employee approval requests

The inbound importer transfers actual `approval.request` records created by employees and their `approval.approver` rows. It does not import `approval.category` records (request types); categories are reference-matched by name and created locally if missing. Attachments and binary fields are excluded. Existing Odoo.sh employees are reused by matching their user login/email to avoid duplicate `(user_id, company_id)` employee records.

### Inbound reference matching and automatic creation

- Existing Odoo.sh employees are reused by mapped user, work email, or a unique exact name. If the employee is already linked to the same user, the importer reuses it and updates the inbound mapping instead of attempting a duplicate employee.
- Approval categories are reference records: the importer matches an existing category by name and creates a local category when no unique match exists. Categories are not imported as a separate synchronization stream.
- If an approval approver's Online user cannot be matched to an active local user, the importer creates an active internal placeholder user with a generated `online_approver_*` login, no password, and no invitation. This is required because Odoo rejects archived users as approval approvers. Review these placeholder users in Settings > Users and map them to real users when appropriate.
- No attachments or binary files are transferred.


## Hotfix 18.0.1.3.0

- Employee imports prefer an existing employee linked to the resolved user in the active company,
  including archived employees, and avoid assigning a user already owned by another employee.
- Missing Online employee names are re-read; a deterministic placeholder is used only when the
  source still provides no name.
- Duplicate local approval-category names are resolved deterministically rather than aborting
  every request. The selected category is persisted in the Online-ID mapping. Verify that the
  selected category represents the intended workflow; duplicate categories should be cleaned up.

## Hotfix 18.0.1.3.1

- Approval approver imports now resolve `request_id` and `user_id` before creating a line.
- If the approval request already generated an approver line from its category, the importer reuses and updates that line instead of creating another one.
- Repeated Online approver rows for the same request/user are mapped to one local row, matching Odoo's singleton assumption in `approval.request` user-status computation.
- After an approver import, the importer also repairs duplicate request/user rows left by earlier sync runs for requests mapped by the same sync configuration. It keeps the row with the most advanced approval status and redirects the inbound ID mappings to it.
- The importer now includes stored approver status/sequence/required fields when those fields are available and writable through the ORM.
- This hotfix does not add attachment/binary transfer or arbitrary custom one2many synchronization; those remain excluded by the existing importer design.


## Hotfix 18.0.1.3.2 — Approval decision round-trip

This revision adds an outbound approval-decision pass before each Online-to-Odoo.sh import:

- Mapped `approval.approver` statuses changed in Odoo.sh are written to the matching Online approver before inbound import runs.
- The remote status is read back for verification. If the push fails, that Online approver is excluded from inbound status import for that run, preventing a stale Online status from overwriting the local decision. The failure is recorded in Sync History.
- Approver relation resolution now explicitly falls back to the `IN|approval.request` mapping and resolves the Online user before attempting to match/create the local approver line. Missing mappings produce an actionable error rather than a generic unresolved-relations message.
- Employee imports retry without changing `user_id` when the employee/user trust-link operation is rejected, preserving the employee record data without attempting a privileged trust-state change.

**Important operational notes**

- The outbound approval sync requires the Online integration account to have write access to `approval.approver.status`.
- This sync writes the stored approver `status` field and verifies it. It does not reproduce a user click or create an approval activity/chatter entry on Online. Test the exact approval workflow on a staging database before production deployment.
- Only records with existing inbound ID mappings can be pushed. Run the inbound import once after upgrading so previously failed approver rows can be mapped.
- This release has been syntax/XML validated only; it has not been tested against the user's live Odoo Online/Odoo.sh databases.


## Hotfix 18.0.1.3.3

- Repairs missing inbound `approval.request` mappings when an approver row refers to a request whose map is absent, using a unique exact match or creating the missing local request instead of failing immediately.
- Repairs stale/deleted Online `approval.approver` IDs by locating the Online approver through the mapped request/user pair or recreating the line, then updating the inbound mapping.
- Avoids importing `hr.employee.user_id` directly because customized Odoo trust-state inverses can reject that operation; employee records still import without attempting to change account trust/linkage.
- Python/XML static validation is not a substitute for a live two-database Odoo test. Back up both databases and validate on staging before production.


### Hotfix 18.0.1.3.4
- Disabled all automatic `res.users` creation during synchronization. Missing user identities are skipped; approval requests continue importing without manufacturing an approver account.
- Existing archived users can be resolved and reused as historical identities without reactivation.
- SH approval lines with no unique existing Online user mapping are skipped safely and are not pushed against an unrelated user.
- Removed the unsupported `sequence` field from Online `approval.approver` creation (Odoo 20).
- Employee imports explicitly omit `user_id` to avoid trust/untrust permission errors.
- Existing approval request/approver records are matched before creation to reduce duplicates.
