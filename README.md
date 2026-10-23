# CURE — Clinical Urgency & Risk Evaluation

CURE is an academic decision-support prototype for preliminary patient urgency assessment. It is not a diagnostic system, is not clinically validated, and must never be used to delay emergency care.

## Status

Core prototype workflows are implemented: authentication/RBAC, patient profile/history, protected local reports with local extraction and verification, adaptive questionnaire/screening snapshots, rule-based emergency flags, triage routing, doctor review, administrator account management, and role workspaces. The experimental NHAMCS model pipeline is research-only and is not loaded by CURE or used to route patients.

See `BACKLOG.md`, `HANDOFF.md`, and `DECISIONS.md` for the authoritative status and decisions.

For a fast local walkthrough of patient, triage, doctor, and admin roles, follow [`DEMO_GUIDE.md`](DEMO_GUIDE.md).

For the full Windows PowerShell setup, testing, demo upload, and optional ML commands, follow [`RUN_GUIDE.md`](RUN_GUIDE.md).

## Start locally

1. Copy `.env.example` to `.env` and replace development placeholder secrets.
2. Run `docker compose up --build`.
3. Open `http://localhost:5173`, the API documentation at `http://localhost:8000/docs`, and verify `http://localhost:8000/api/v1/health`.

Run `docker compose down` to stop services. Add `--volumes` only when intentionally deleting local PostgreSQL data.

## Test

Run `docker compose --profile test run --build --rm backend-test` to execute the current regression suite.

## Experimental ML evaluation

The CDC NHAMCS 2022 ED public-use data archive is not committed. Download the official `ed2022_sas.zip` file from the [CDC NHAMCS SAS files](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHAMCS/sas/) and extract `ed2022_sas.sas7bdat` under `data/nhamcs/`. From the repository root, build and run the isolated training image:

```powershell
docker build -f ml/Dockerfile -t cure-ml:local ml
New-Item -ItemType Directory -Force ml/artifacts | Out-Null
docker run --rm -v "${PWD}/data/nhamcs:/data:ro" -v "${PWD}/ml/artifacts:/artifacts" cure-ml:local --input /data/ed2022_sas.sas7bdat --output /artifacts
```

This compares logistic regression and random forest against NHAMCS's original 1–5 provider-recorded triage levels with validation-based candidate selection and a held-out test set. Outputs include per-class metrics, confusion matrices, feature missingness, and local model artifacts. Scores describe agreement with historical triage labels only; they are not clinical outcomes or validation. Do not use the artifacts in the app or with real patients. Clinician review and external validation remain required.

To run the backend tests, use `docker compose --env-file .env.example --profile test run --build --rm backend-test`. A successful frontend production build is `docker compose --env-file .env.example run --no-deps --rm frontend npm run build`.

## Development administrator

To create a one-time development administrator, set `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` in your local `.env`, start the services, then run `docker compose exec backend python -m app.bootstrap_admin`. Public registration can only create patient accounts.

## Testing

The current regression suite includes API authorization, questionnaire missingness, screening history/snapshots, emergency rules, report failure and assigned access, account management, triage priority/routing, doctor review, and deletion rollback coverage.
