# CURE Handoff

## Current status

Initial setup, schema migration, patient profile/history, report verification, screening snapshots, questionnaire persistence, emergency flags, and core role workflows are implemented. User verified Docker startup, patient registration, protected-token access, profile updates, report upload/listing/verification, and prior automated tests. ML remains intentionally unavailable pending approved data.

The workspace (`D:\Dev\Backend\CURE-app`) was empty and is now an initialized Git repository. There was no existing implementation to preserve.

## Current task

`P5-02` — complete screening workflow verification, then test doctor/triage/admin authorization boundaries.

## Exact next steps

1. Run the expanded API tests for questionnaire persistence, snapshot immutability, emergency precedence, RBAC denial, deletion confirmation, and report-validation failure.
2. Create a development administrator, then manually verify triage routing and doctor review.
3. Select data only after authorized access and documented label review.

## Intended architecture and data flow

- React frontend communicates with a FastAPI modular monolith using REST APIs.
- FastAPI owns authentication/RBAC, patient data, reports, questionnaires, screenings, triage, feedback, analytics, and audit logging.
- PostgreSQL stores normalized relational data; protected local storage retains uploaded reports.
- Local PDF text extraction/OCR feeds unverified report data; patient verification creates separate confirmed structured data.
- A versioned scikit-learn pipeline will evaluate urgency only after a real, documented dataset is selected. Emergency-warning rules will remain independent of ML inference.

## Important files

- `compose.yaml` — React, FastAPI, and PostgreSQL development services.
- `backend/app/main.py` — FastAPI application and `/api/v1/health` endpoint.
- `backend/app/db/models.py` — normalized ORM foundation for accounts, profiles/history, reports, assignments, screenings, reviews, model versions, and audit events.
- `backend/app/api/auth.py` — patient-only registration, login, JWT current-user dependency, and reusable role guard.
- `backend/alembic/versions/20261023_01_initial_schema.py` — explicit initial PostgreSQL schema migration.
- `frontend/src/main.tsx` — minimal React entrypoint and safety statement.
- `BACKLOG.md` — canonical task status and acceptance criteria.
- `DECISIONS.md` — technical and clinical-safety decisions.
- `HANDOFF.md` — this resumable status record.

## Dataset and model status

No dataset has been selected, imported, or trained. `docs/DATASET_DISCOVERY.md` records MIMIC-IV-ED as the preferred but access-restricted research candidate and CDC NHAMCS as a public candidate requiring inspection. No urgency-label mapping, model, metric, explanation, or clinical performance result exists yet.

## Commands

Verified: `python -m py_compile backend/app/main.py backend/app/api/health.py backend/app/core/config.py backend/app/api/auth.py backend/app/core/security.py backend/app/db/base.py backend/app/db/models.py backend/app/db/session.py backend/alembic/env.py backend/alembic/versions/20261023_01_initial_schema.py` and `docker compose --env-file .env.example config --quiet` both exited successfully on 2026-10-23. The user verified services start locally, migration application, and patient registration with HTTP 201. The coding session itself cannot access the Windows Docker API pipe.

To start the app, copy `.env.example` to `.env`, choose local development-only secrets, then run `docker compose up --build`. Runtime/image-build verification has not yet been performed.

## Known blockers and risks

- Automated login/authorization tests and authentication audit events remain to be implemented. The coding session itself cannot access the Windows Docker API pipe.
- Dataset selection requires an evidence-based public-data review before any ML implementation or performance claim.
- Emergency rules require reputable clinical guidance and appropriate clinical review; none are defined yet.

## Next task for another agent

Execute `P1-03` from `BACKLOG.md`, update all three tracking files with actual commands/results, and do not mark it complete until the configured services start or any blockers are documented.
