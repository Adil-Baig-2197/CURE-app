# Privacy, retention, and prototype limitations

CURE is an academic prototype and does not claim legal, regulatory, HIPAA, GDPR, or medical-device compliance.

## Access and storage

- Report originals are stored only in the protected backend storage volume, never exposed by a static frontend path.
- Patient-specific API operations enforce authentication and role checks in the FastAPI backend.
- Raw report extraction remains separate from patient-verified information.
- Audit events record security-relevant account, report, questionnaire, triage, and review actions without storing passwords or bearer tokens.

## Retention policy for this prototype

- An authenticated patient may request deletion with the explicit `DELETE_MY_DATA` confirmation. Accounts with screenings are ineligible until retention review. For eligible accounts, report originals are moved into a protected quarantine folder before the database transaction; a failed transaction restores the files, and a successful transaction removes the staged files.
- If final filesystem cleanup fails after database commit, the report can remain in the protected `.deletion-pending` folder and is logged for operator cleanup. This prototype has no durable cleanup worker or alerting; operators must monitor the protected storage volume.
- Accounts with historical screenings receive an explicit ineligible response until a retention-review workflow is implemented; screening and audit records are not silently altered.
- Historical screenings and audit events must not be silently changed by later profile updates; current schema therefore preserves their snapshots.
- A future deletion workflow must explicitly resolve clinical-record retention exceptions and remove corresponding protected files, not merely database rows.

## Known limitations

This prototype does not yet implement a complete verified deletion request workflow, encryption at rest, key management, breach handling, data residency controls, a durable quarantine cleanup worker, or a regulatory retention schedule. Do not use it with real patient data outside an approved academic environment.
