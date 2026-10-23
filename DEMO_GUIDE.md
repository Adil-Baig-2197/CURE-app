# CURE quick demo

This guide is for a local academic demo with synthetic accounts and data. Do not enter real patient information. CURE and its emergency rules are not clinically validated, and the experimental ML model is not used in the app.

## Start the app

1. From the repository root, copy `.env.example` to `.env`. Set a unique local `POSTGRES_PASSWORD` and a long random `JWT_SECRET_KEY`. Set `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` to demo-only credentials (the password must be at least 12 characters).
2. Start the services: `docker compose up --build -d`.
3. Create the initial admin once: `docker compose exec backend python -m app.bootstrap_admin`.
4. Open the frontend at [http://localhost:5173](http://localhost:5173). API docs are at [http://localhost:8000/docs](http://localhost:8000/docs), and health is at [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health).

## Walk through the roles

1. **Admin:** sign in with the bootstrap credentials. In the role dashboard, create one `doctor` account and one `triage_staff` account using demo-only email addresses and passwords. Admin also has aggregate analytics.
2. **Patient:** sign out and register a synthetic patient with a separate email. Complete profile/history and submit the symptom questionnaire. Use fictional, non-identifying details. The result is saved to the patient's screening history.
3. **Triage staff:** sign in using the account created by admin. Open the intake queue, select the new screening, and route it to the demo doctor.
4. **Doctor:** sign in as the assigned doctor, open the assigned screening, review it, or record a correction with a reason. The doctor should only see patients assigned by triage.
5. Return to **Admin** to show aggregate counts and role/account controls.

## If an account is locked out

Use another active administrator account to reactivate it. The system prevents disabling or demoting the last active administrator. For a clean local demo database only, `docker compose down --volumes` deletes the local PostgreSQL and report-storage volumes; this permanently removes demo data.

## Quick verification

Run the backend regression suite with `docker compose --env-file .env.example --profile test run --build --rm backend-test` (or use your local `.env` instead of `.env.example`). Build the frontend with `docker compose --env-file .env.example run --no-deps --rm frontend npm run build`.

For the previous implementation verification and limits, see `HANDOFF.md` and `BACKLOG.md`.
