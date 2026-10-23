# CURE — Clinical Urgency & Risk Evaluation

CURE is an academic decision-support prototype for preliminary patient urgency assessment. It is not a diagnostic system, is not clinically validated, and must never be used to delay emergency care.

## Status

Core prototype workflows are implemented: authentication/RBAC, patient profile/history, protected local reports with local extraction and verification, questionnaire/screening snapshots, rule-based emergency flags, triage routing, doctor review, administrator account management, and basic role workspaces. ML prediction remains deliberately unavailable pending authorized data access and evaluation.

See `BACKLOG.md`, `HANDOFF.md`, and `DECISIONS.md` for the authoritative status and decisions.

## Start locally

1. Copy `.env.example` to `.env` and replace development placeholder secrets.
2. Run `docker compose up --build`.
3. Open `http://localhost:5173`, the API documentation at `http://localhost:8000/docs`, and verify `http://localhost:8000/api/v1/health`.

Run `docker compose down` to stop services. Add `--volumes` only when intentionally deleting local PostgreSQL data.

## Test

Run `docker compose --profile test run --build --rm backend-test` to execute the current regression suite.

No dataset or trained model has been selected, so no model-performance, calibration, report-extraction, or clinical-validity claims are made.

## Development administrator

To create a one-time development administrator, set `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` in your local `.env`, start the services, then run `docker compose exec backend python -m app.bootstrap_admin`. Public registration can only create patient accounts.

## Testing

Run the test container with `docker compose --profile test run --build --rm backend-test`. It applies the current migration and runs password/JWT unit tests plus registration, login, protected-route, and invalid-credential API tests against the Compose PostgreSQL service. Runtime API and database tests will be expanded as each workflow is added.
