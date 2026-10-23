# CURE Handoff

## Current status

CURE is a React/FastAPI/PostgreSQL prototype with authentication and role-based access, patient profiles/history, protected report upload and verification, adaptive screening questionnaire and history, emergency flags, triage and assigned-doctor workflows, account administration, analytics, and audit events. The requested backlog implementation and exploratory ML training have been completed to the prototype/research scope listed in `BACKLOG.md`.

Verification on 2026-10-23: backend suite **18 passed** (one Starlette deprecation warning); frontend production TypeScript/Vite build passes after the latest frontend fix; Compose images rebuilt and services started; PostgreSQL reported healthy, `/api/v1/health` returned `ok`, and the frontend returned HTTP 200. Browser check confirmed the clean login page and readable invalid-email/incorrect-password feedback. Full authenticated role-to-role browser verification has not been performed.

`DEMO_GUIDE.md` now gives the quick local setup and patient → triage → doctor → admin walkthrough. API validation errors are formatted as readable messages instead of `[object Object]`.

For the user-requested demo deliverables, `RUN_GUIDE.md` documents Windows PowerShell setup, run, account bootstrap, role walkthrough, upload, test, build, optional model training, and shutdown commands. The synthetic upload files are `output/pdf/cure_synthetic_demo_lab_report.pdf`, `demo-assets/images/cure_synthetic_demo_lab_report.png`, and `demo-assets/images/cure_synthetic_demo_visit_note.jpg`. The PDF and both image formats were visually reviewed; the backend extraction function returned non-empty text for each. All values are fictional and carry prominent non-clinical-use labels.

## ML status and limits

The reproducible pipeline inspected CDC 2022 NHAMCS ED data, trained logistic regression and random forest baselines, and saved research artifacts locally under ignored `ml/artifacts/`. Validation weighted macro-F1 selected logistic regression provisionally (0.3154 vs 0.2259). On the held-out test set, logistic regression weighted macro-F1 was 0.3576; random forest scored 0.2325. Rare urgency classes had poor recall, including only 4/21 immediate cases and 5/46 nonurgent cases recalled by the selected baseline. These results are not clinically adequate and the models are not connected to CURE or patient decisions.

No claim of clinical validity, safety, calibration, fairness, or generalization is supported. Do not integrate or deploy the model without independent clinical validation and additional data and evaluation. See `docs/DATASET_DISCOVERY.md`.

## Remaining external work

1. A qualified clinician must review and approve the emergency rules and urgent guidance in `docs/EMERGENCY_RULES.md` before any real patient use.
2. Clinical validation and external testing are needed before any predictive model could be considered for integration. The backlog marks model integration as blocked on that validation.
3. Privacy documentation notes that account deletion does not yet have a durable cleanup worker; operator monitoring and a retention review are needed before production use.
4. Full role-by-role browser workflow tests, production deployment hardening, and real-world operational/compliance review are outside this verified prototype pass.

## Architecture and important files

- `backend/app/api/questionnaire.py`, `backend/app/services/emergency.py` — questionnaire and independent safety flags.
- `backend/app/api/screenings.py` — screening creation, snapshots, patient history/detail.
- `backend/app/api/workflow.py` — triage, doctor review, assignment access, admin functions.
- `backend/app/api/patients.py` — patient data and privacy deletion behavior.
- `frontend/src/main.tsx`, `frontend/src/RoleDashboard.tsx` — patient and staff interfaces.
- `ml/train_nhamcs.py`, `ml/requirements.txt`, `ml/Dockerfile` — reproducible research training pipeline.
- `docs/DATASET_DISCOVERY.md`, `docs/EMERGENCY_RULES.md`, `docs/PRIVACY_AND_RETENTION.md` — evidence and limitations.
- `BACKLOG.md`, `DECISIONS.md` — canonical task status and decisions.

## Commands

Start development services: `docker compose up --build` (set local secrets as described in `README.md`).

Backend regression suite: `docker compose --env-file .env.example --profile test run --build --rm backend-test`.

Train/evaluate research baselines: see `README.md` and `ml/README.md`; CDC data and generated artifacts are local and ignored by Git.

Do not use experimental ML outputs or unreviewed emergency rules for patient care.
