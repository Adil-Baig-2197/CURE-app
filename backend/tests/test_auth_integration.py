from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_patient_can_register_login_and_access_only_own_identity() -> None:
    email = f"patient-{uuid4().hex}@cure-demo.org"
    password = "SafeLocalPass_2026!"

    registration = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert registration.status_code == 201
    token = registration.json()["access_token"]

    identity = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert identity.status_code == 200
    assert identity.json()["email"] == email
    assert identity.json()["role"] == "patient"

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_invalid_credentials_and_invalid_tokens_are_rejected() -> None:
    login = client.post("/api/v1/auth/login", json={"email": "missing@cure-demo.org", "password": "SafeLocalPass_2026!"})
    assert login.status_code == 401

    identity = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid-token"})
    assert identity.status_code == 401


def test_patient_can_manage_only_their_own_profile_and_history() -> None:
    email = f"patient-{uuid4().hex}@cure-demo.org"
    registration = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "SafeLocalPass_2026!"}
    )
    token = registration.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    unauthenticated = client.get("/api/v1/patients/me/profile")
    assert unauthenticated.status_code == 401

    profile = client.put(
        "/api/v1/patients/me/profile",
        headers=headers,
        json={
            "date_of_birth": "1998-04-15",
            "sex_at_birth": "female",
            "phone_number": "5550100",
            "no_reports_declared": True,
        },
    )
    assert profile.status_code == 200
    assert profile.json()["no_reports_declared"] is True

    history = client.put(
        "/api/v1/patients/me/history",
        headers=headers,
        json={"conditions": ["asthma"], "medications": ["inhaler"], "notes": "Patient-provided history."},
    )
    assert history.status_code == 200
    assert history.json()["conditions"] == ["asthma"]

    screening = client.post(
        "/api/v1/screenings",
        headers=headers,
        json={"responses": {"symptom": "cough"}, "missing_fields": ["duration"]},
    )
    assert screening.status_code == 201
    screening_id = screening.json()["id"]
    assert screening.json()["medical_snapshot"]["conditions"] == ["asthma"]

    changed_history = client.put(
        "/api/v1/patients/me/history",
        headers=headers,
        json={"conditions": ["migraine"], "medications": [], "notes": None},
    )
    assert changed_history.status_code == 200

    historical = client.get(f"/api/v1/screenings/{screening_id}", headers=headers)
    assert historical.status_code == 200
    assert historical.json()["medical_snapshot"]["conditions"] == ["asthma"]


def test_emergency_warning_precedes_any_prediction() -> None:
    email = f"patient-{uuid4().hex}@cure-demo.org"
    registration = client.post("/api/v1/auth/register", json={"email": email, "password": "SafeLocalPass_2026!"})
    headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
    submission = client.post(
        "/api/v1/questionnaire/submit",
        headers=headers,
        json={"responses": {"symptoms": ["chest_pain"], "severity": "severe", "duration": "10 minutes", "progression": "worsening", "chest_pain_character": "pressure", "severe_breathing_difficulty": "no", "chest_pressure_or_spreading": "yes", "face_droop": "no", "one_sided_weakness": "no", "speech_difficulty": "no", "unresponsive": "no"}},
    )
    assert submission.status_code == 201
    assert submission.json()["emergency_warning"] is True
    assert "do not wait" in submission.json()["message"].lower()


def test_patient_cannot_access_triage_or_administration() -> None:
    email = f"patient-{uuid4().hex}@cure-demo.org"
    registration = client.post("/api/v1/auth/register", json={"email": email, "password": "SafeLocalPass_2026!"})
    headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
    assert client.get("/api/v1/triage/queue", headers=headers).status_code == 403
    assert client.post("/api/v1/admin/accounts", headers=headers, json={"email": "doctor@cure-demo.org", "password": "SafeLocalPass_2026!", "role": "doctor"}).status_code == 403


def test_eligible_patient_deletion_requires_explicit_confirmation() -> None:
    email = f"patient-{uuid4().hex}@cure-demo.org"
    registration = client.post("/api/v1/auth/register", json={"email": email, "password": "SafeLocalPass_2026!"})
    headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
    assert client.request("DELETE", "/api/v1/patients/me", headers=headers, json={"confirmation": "no"}).status_code == 422
    assert client.request("DELETE", "/api/v1/patients/me", headers=headers, json={"confirmation": "DELETE_MY_DATA"}).status_code == 204
    assert client.post("/api/v1/auth/login", json={"email": email, "password": "SafeLocalPass_2026!"}).status_code == 401


def test_unsupported_report_upload_is_rejected() -> None:
    email = f"patient-{uuid4().hex}@cure-demo.org"
    registration = client.post("/api/v1/auth/register", json={"email": email, "password": "SafeLocalPass_2026!"})
    headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
    response = client.post("/api/v1/reports", headers=headers, files={"upload": ("report.txt", b"not a medical report", "text/plain")})
    assert response.status_code == 415
