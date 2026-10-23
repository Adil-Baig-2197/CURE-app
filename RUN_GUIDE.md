# CURE - Windows run and demo guide

This guide uses PowerShell from the repository root. It assumes Docker Desktop is installed and running. Use synthetic data only. CURE is an academic prototype, not a diagnostic or emergency-care system. Do not use it to make care decisions.

## 1. Open the project folder

```powershell
Set-Location 'C:\Users\Huzaif\Desktop\Cure\CURE-app'
docker version
```

If `docker version` fails, start Docker Desktop and wait until its engine is running.

## 2. Set up local configuration once

```powershell
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env' }
notepad .env
```

In `.env`, replace `POSTGRES_PASSWORD` and `JWT_SECRET_KEY` with local-only values. Set `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` to demo-only values; use at least 12 characters for the password. Save the file. Do not commit `.env` or share these demo credentials.

## 3. Start CURE

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/health'
```

Expected: the database is `healthy`, the API health response says `ok`, and the frontend container is `Up`. Open:

- Frontend: [http://localhost:5173](http://localhost:5173)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## 4. Create demo accounts and show the workflows

Create the first administrator once:

```powershell
docker compose exec backend python -m app.bootstrap_admin
```

Then use the browser:

1. Sign in as the admin. Create demo-only accounts for `doctor` and `triage_staff` in the admin workspace.
2. Sign out. Create a patient account using the patient registration button. Use a fictional name and fictional history.
3. Upload the [synthetic PDF](output/pdf/cure_synthetic_demo_lab_report.pdf) or either image in [`demo-assets/images`](demo-assets/images). Review extracted text as unverified and use the patient verification control to confirm only the fictional demo content.
4. Complete the symptom questionnaire and submit a screening.
5. Sign out and enter the triage account. Find the screening in the queue and route it to the demo doctor.
6. Sign out and enter the assigned doctor account. Open the screening and record a review. Only use fabricated demo responses.
7. Sign back into admin to show aggregate analytics and account management.

The upload examples are intentionally synthetic; they are for testing upload and text extraction only, not clinical advice.

## 5. Run checks

Run the backend integration suite:

```powershell
docker compose --profile test run --build --rm backend-test
```

Build the production frontend bundle:

```powershell
docker compose run --no-deps --rm frontend npm run build
```

Inspect service logs if something fails:

```powershell
docker compose logs --tail 100 backend frontend db
```

## 6. Optional: train the research-only ML comparison

The CDC dataset is not included in Git. If `data\nhamcs\ed2022_sas.sas7bdat` is missing, download the CDC 2022 NHAMCS ED SAS archive from the link in `README.md` and extract the `.sas7bdat` file into `data\nhamcs`. Then run:

```powershell
if (-not (Test-Path 'data\nhamcs\ed2022_sas.sas7bdat')) { throw 'Place ed2022_sas.sas7bdat in data\nhamcs first.' }
docker build -f ml/Dockerfile -t cure-ml:local ml
New-Item -ItemType Directory -Force 'ml\artifacts' | Out-Null
docker run --rm -v "${PWD}/data/nhamcs:/data:ro" -v "${PWD}/ml/artifacts:/artifacts" cure-ml:local --input /data/ed2022_sas.sas7bdat --output /artifacts
```

This trains research baselines only. The model is not connected to CURE, and its current performance is not adequate for clinical use.

## 7. Stop CURE

```powershell
docker compose down
```

This stops containers and keeps local database and report storage. Do not add `--volumes` unless you intentionally want to permanently delete all local demo data.

## Completion status

The academic prototype and demo startup flows are implemented. The project is **not clinically or production ready**: emergency rules need qualified clinician review, the experimental model is not suitable for patient decisions, and production privacy/operations and full cross-role end-to-end verification remain. See `BACKLOG.md` and `HANDOFF.md` for the verified status.
