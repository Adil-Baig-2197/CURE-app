from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from app.api.patients import DeletionRequest, delete_my_eligible_data
from app.core.security import hash_password
from app.db.models import AuditEvent, DoctorPatientAssignment, MedicalReport, PatientProfile, ReportStatus, Screening, User, UserRole, UrgencyLevel
from app.db.session import SessionLocal
from app.main import app
from app.services.emergency import evaluate


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


def test_emergency_rules_cover_all_explicit_yes_flags_and_ignore_no() -> None:
    triggers = ["severe_breathing_difficulty", "blue_or_grey_skin", "chest_pressure_or_spreading", "face_droop", "one_sided_weakness", "speech_difficulty", "sudden_confusion", "unresponsive"]
    assert evaluate({key: False for key in triggers}) == []
    for trigger in triggers:
        assert evaluate({trigger: True}), f"Expected emergency warning for {trigger}"
    assert len(evaluate({"face_droop": True, "speech_difficulty": True})) == 1


def test_questionnaire_missingness_optional_answers_and_applicability() -> None:
    headers = register_patient()
    response = client.post("/api/v1/questionnaire/submit", headers=headers, json={"responses": {
        "symptoms": ["diarrhea", "nausea"], "associated_symptoms": ["chills"],
        "severity": "moderate", "duration": "since yesterday", "progression": "stable",
        "diarrhea_blood": "no", "headache_onset": "sudden", "free_text": "", "unknown_key": "ignored",
        "severe_breathing_difficulty": "no", "chest_pressure_or_spreading": "no", "face_droop": "no",
        "one_sided_weakness": "no", "speech_difficulty": "no", "unresponsive": "no",
    }})
    assert response.status_code == 201
    screening = client.get("/api/v1/screenings", headers=headers).json()[0]
    assert "free_text" not in screening["missing_fields"]
    assert "headache_onset" not in screening["missing_fields"]
    assert screening["responses"]["associated_symptoms"] == ["chills"]
    assert "unknown_key" not in screening["responses"]
    assert "headache_onset" not in screening["responses"]
    with SessionLocal() as db:
        event = db.scalar(select(AuditEvent).where(AuditEvent.resource_id == screening["id"], AuditEvent.action == "questionnaire.submit"))
        assert event is not None
    questions = client.get("/api/v1/questionnaire/questions?selected=diarrhea&selected=fainting", headers=headers)
    ids = {question["id"] for question in questions.json()}
    assert {"associated_symptoms", "diarrhea_blood", "fainting_recovered"} <= ids
    assert questions.json()[0]["id"] == "severe_breathing_difficulty"


def test_admin_can_manage_accounts_without_locking_out_last_admin() -> None:
    suffix = uuid4().hex
    admin_email = f"manage-admin-{suffix}@cure-demo.org"
    doctor_email = f"manage-doctor-{suffix}@cure-demo.org"
    with SessionLocal() as db:
        admin = User(email=admin_email, password_hash=hash_password("SafeLocalPass_2026!"), role=UserRole.ADMINISTRATOR)
        db.add(admin); db.commit()
    admin_login = client.post("/api/v1/auth/login", json={"email": admin_email, "password": "SafeLocalPass_2026!"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    assert client.get("/api/v1/admin/analytics", headers=register_patient()).status_code == 403
    assert client.get("/api/v1/admin/analytics", headers=admin_headers).status_code == 200
    created = client.post("/api/v1/admin/accounts", headers=admin_headers, json={"email": doctor_email, "password": "SafeLocalPass_2026!", "role": "doctor"})
    assert created.status_code == 200
    changed = client.patch(f"/api/v1/admin/accounts/{created.json()['id']}", headers=admin_headers, json={"role": "triage_staff"})
    assert changed.status_code == 200 and changed.json()["role"] == "triage_staff"
    disabled = client.patch(f"/api/v1/admin/accounts/{created.json()['id']}", headers=admin_headers, json={"is_active": False})
    assert disabled.status_code == 200 and disabled.json()["is_active"] is False
    assert client.post("/api/v1/auth/login", json={"email": doctor_email, "password": "SafeLocalPass_2026!"}).status_code == 401
    admin_id = client.get("/api/v1/auth/me", headers=admin_headers).json()["id"]
    self_disable = client.patch(f"/api/v1/admin/accounts/{admin_id}", headers=admin_headers, json={"is_active": False})
    assert self_disable.status_code == 409


def test_triage_queue_prioritizes_emergency_then_urgency() -> None:
    triage_email = f"queue-triage-{uuid4().hex}@cure-demo.org"
    with SessionLocal() as db:
        db.add(User(email=triage_email, password_hash=hash_password("SafeLocalPass_2026!"), role=UserRole.TRIAGE_STAFF))
        db.commit()
    triage_login = client.post("/api/v1/auth/login", json={"email": triage_email, "password": "SafeLocalPass_2026!"})
    headers = {"Authorization": f"Bearer {triage_login.json()['access_token']}"}
    rows: dict[str, str] = {}
    for label in ("routine-low", "routine-high", "emergency-low"):
        patient_headers = register_patient()
        created = client.post("/api/v1/screenings", headers=patient_headers, json={"responses": {"case": label}, "missing_fields": []})
        assert created.status_code == 201
        rows[label] = created.json()["id"]
    with SessionLocal() as db:
        for label, screening_id in rows.items():
            screening = db.scalar(select(Screening).where(Screening.id == screening_id))
            screening.predicted_urgency = UrgencyLevel.HIGH if label == "routine-high" else UrgencyLevel.LOW
            screening.emergency_warning = label == "emergency-low"
        db.commit()
    queue = client.get("/api/v1/triage/queue", headers=headers)
    assert queue.status_code == 200
    positions = {item["id"]: index for index, item in enumerate(queue.json())}
    assert positions[rows["emergency-low"]] < positions[rows["routine-high"]] < positions[rows["routine-low"]]


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


def test_report_files_are_restored_if_account_deletion_transaction_fails(tmp_path, monkeypatch) -> None:
    email = f"delete-report-{uuid4().hex}@cure-demo.org"
    registration = client.post("/api/v1/auth/register", json={"email": email, "password": "SafeLocalPass_2026!"})
    headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
    storage_key = f"{uuid4().hex}.pdf"
    original = b"protected report fixture"
    (tmp_path / storage_key).write_bytes(original)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        profile = db.scalar(select(PatientProfile).where(PatientProfile.user_id == user.id))
        db.add(MedicalReport(patient_id=profile.id, original_filename="report.pdf", storage_key=storage_key, content_type="application/pdf", byte_size=len(original), status=ReportStatus.AWAITING_VERIFICATION))
        db.commit()
    monkeypatch.setattr("app.api.patients.get_settings", lambda: type("Settings", (), {"report_storage_path": tmp_path})())
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        profile = db.scalar(select(PatientProfile).where(PatientProfile.user_id == user.id))
        def fail_commit():
            raise RuntimeError("simulated database failure")
        monkeypatch.setattr(db, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="simulated database failure"):
            delete_my_eligible_data(DeletionRequest(confirmation="DELETE_MY_DATA"), profile, user, db)
    assert (tmp_path / storage_key).read_bytes() == original
    assert list((tmp_path / ".deletion-pending").glob("*.pending")) == []
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        profile = db.scalar(select(PatientProfile).where(PatientProfile.user_id == user.id))
        delete_my_eligible_data(DeletionRequest(confirmation="DELETE_MY_DATA"), profile, user, db)
    assert not (tmp_path / storage_key).exists()
    assert list((tmp_path / ".deletion-pending").glob("*.pending")) == []
    assert client.post("/api/v1/auth/login", json={"email": email, "password": "SafeLocalPass_2026!"}).status_code == 401


def test_unsupported_report_upload_is_rejected() -> None:
    email = f"patient-{uuid4().hex}@cure-demo.org"
    registration = client.post("/api/v1/auth/register", json={"email": email, "password": "SafeLocalPass_2026!"})
    headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
    response = client.post("/api/v1/reports", headers=headers, files={"upload": ("report.txt", b"not a medical report", "text/plain")})
    assert response.status_code == 415
client = TestClient(app)


def register_patient() -> dict[str, str]:
    email = f"history-{uuid4().hex}@cure-demo.org"
    registration = client.post("/api/v1/auth/register", json={"email": email, "password": "SafeLocalPass_2026!"})
    assert registration.status_code == 201
    return {"Authorization": f"Bearer {registration.json()['access_token']}"}


def test_screening_history_is_paginated_and_confined_to_patient() -> None:
    first_headers = register_patient()
    second_headers = register_patient()
    created = client.post("/api/v1/screenings", headers=first_headers, json={"responses": {"symptoms": ["cough"]}, "missing_fields": ["duration"]})
    assert created.status_code == 201
    first_id = created.json()["id"]

    history = client.get("/api/v1/screenings?limit=1&offset=0", headers=first_headers)
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["id"] == first_id
    assert history.json()[0]["responses"] == {"symptoms": ["cough"]}
    assert history.json()[0]["missing_fields"] == ["duration"]
    assert history.json()[0]["predicted_urgency"] is None
    assert history.json()[0]["emergency_warning"] is False

    assert client.get("/api/v1/screenings", headers=second_headers).json() == []
    assert client.get(f"/api/v1/screenings/{first_id}", headers=second_headers).status_code == 404
    assert client.get("/api/v1/screenings?limit=1000", headers=first_headers).status_code == 422
def test_triage_routing_doctor_review_and_audit_workflow() -> None:
    suffix = uuid4().hex
    patient_email = f"workflow-patient-{suffix}@cure-demo.org"
    admin_email = f"workflow-admin-{suffix}@cure-demo.org"
    patient_registration = client.post("/api/v1/auth/register", json={"email": patient_email, "password": "SafeLocalPass_2026!"})
    assert patient_registration.status_code == 201
    patient_headers = {"Authorization": f"Bearer {patient_registration.json()['access_token']}"}

    with SessionLocal() as db:
        admin = User(email=admin_email, password_hash=hash_password("SafeLocalPass_2026!"), role=UserRole.ADMINISTRATOR)
        db.add(admin)
        db.commit()

    admin_login = client.post("/api/v1/auth/login", json={"email": admin_email, "password": "SafeLocalPass_2026!"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    doctor_email = f"doctor-{suffix}@cure-demo.org"
    unassigned_doctor_email = f"unassigned-doctor-{suffix}@cure-demo.org"
    triage_email = f"triage-{suffix}@cure-demo.org"
    doctor_create = client.post("/api/v1/admin/accounts", headers=admin_headers, json={"email": doctor_email, "password": "SafeLocalPass_2026!", "role": "doctor"})
    unassigned_doctor_create = client.post("/api/v1/admin/accounts", headers=admin_headers, json={"email": unassigned_doctor_email, "password": "SafeLocalPass_2026!", "role": "doctor"})
    triage_create = client.post("/api/v1/admin/accounts", headers=admin_headers, json={"email": triage_email, "password": "SafeLocalPass_2026!", "role": "triage_staff"})
    assert doctor_create.status_code == unassigned_doctor_create.status_code == triage_create.status_code == 200
    doctor_login = client.post("/api/v1/auth/login", json={"email": doctor_email, "password": "SafeLocalPass_2026!"})
    unassigned_doctor_login = client.post("/api/v1/auth/login", json={"email": unassigned_doctor_email, "password": "SafeLocalPass_2026!"})
    triage_login = client.post("/api/v1/auth/login", json={"email": triage_email, "password": "SafeLocalPass_2026!"})
    doctor_headers = {"Authorization": f"Bearer {doctor_login.json()['access_token']}"}
    unassigned_doctor_headers = {"Authorization": f"Bearer {unassigned_doctor_login.json()['access_token']}"}
    triage_headers = {"Authorization": f"Bearer {triage_login.json()['access_token']}"}

    screening = client.post("/api/v1/screenings", headers=patient_headers, json={"responses": {"symptoms": ["cough"]}, "missing_fields": []})
    assert screening.status_code == 201
    screening_id = screening.json()["id"]
    assert client.get("/api/v1/doctor/screenings", headers=doctor_headers).json() == []
    assert client.post(f"/api/v1/triage/screenings/{screening_id}/route", headers=triage_headers, json={"doctor_id": doctor_create.json()["id"]}).status_code == 200
    assert client.get("/api/v1/doctor/screenings", headers=doctor_headers).json()[0]["id"] == screening_id
    assert client.get("/api/v1/doctor/screenings", headers=unassigned_doctor_headers).json() == []
    assert client.post(f"/api/v1/doctor/screenings/{screening_id}/review", headers=unassigned_doctor_headers, json={"status": "confirmed"}).status_code == 404

    missing_reason = client.post(f"/api/v1/doctor/screenings/{screening_id}/review", headers=doctor_headers, json={"status": "corrected", "corrected_urgency": "high"})
    assert missing_reason.status_code == 422
    correction_reason = "Doctor reviewed the intake and corrected the category."
    correction = client.post(f"/api/v1/doctor/screenings/{screening_id}/review", headers=doctor_headers, json={"status": "corrected", "corrected_urgency": "high", "correction_reason": correction_reason})
    assert correction.status_code == 200
    history = client.get("/api/v1/screenings", headers=patient_headers)
    assert history.json()[0]["review_status"] == "corrected"

    status_update = client.patch(f"/api/v1/triage/screenings/{screening_id}/status", headers=triage_headers, json={"status": "completed"})
    assert status_update.status_code == 200
    assert status_update.json()["intake_status"] == "completed"
    with SessionLocal() as db:
        event = db.scalar(select(AuditEvent).where(AuditEvent.resource_id == screening_id, AuditEvent.action == "doctor.review"))
        assert event is not None
        assert event.details["corrected_urgency"] == "high"
        assert event.details["correction_reason"] == correction_reason

def test_corrupted_pdf_upload_returns_safe_error() -> None:
    email = f"bad-pdf-{uuid4().hex}@cure-demo.org"
    registration = client.post("/api/v1/auth/register", json={"email": email, "password": "SafeLocalPass_2026!"})
    headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
    response = client.post("/api/v1/reports", headers=headers, files={"upload": ("report.pdf", b"not a valid PDF", "application/pdf")})
    assert response.status_code == 422
    assert "could not be read safely" in response.json()["detail"]
def test_doctor_can_access_only_assigned_verified_reports(tmp_path, monkeypatch) -> None:
    suffix = uuid4().hex
    patient_email = f"reports-patient-{suffix}@cure-demo.org"
    doctor_email = f"reports-doctor-{suffix}@cure-demo.org"
    other_doctor_email = f"reports-other-{suffix}@cure-demo.org"
    patient = client.post("/api/v1/auth/register", json={"email": patient_email, "password": "SafeLocalPass_2026!"})
    patient_headers = {"Authorization": f"Bearer {patient.json()['access_token']}"}
    with SessionLocal() as db:
        profile = db.scalar(select(PatientProfile).join(User, PatientProfile.user_id == User.id).where(User.email == patient_email))
        doctor = User(email=doctor_email, password_hash=hash_password("SafeLocalPass_2026!"), role=UserRole.DOCTOR)
        other_doctor = User(email=other_doctor_email, password_hash=hash_password("SafeLocalPass_2026!"), role=UserRole.DOCTOR)
        db.add_all([doctor, other_doctor])
        db.flush()
        patient_id = profile.id
        db.add(DoctorPatientAssignment(doctor_id=doctor.id, patient_id=patient_id))
        original = b"CURE protected report fixture"
        storage_key = f"{suffix}.pdf"
        (tmp_path / storage_key).write_bytes(original)
        report = MedicalReport(patient_id=patient_id, original_filename="verified-report.pdf", storage_key=storage_key, content_type="application/pdf", byte_size=len(original), status=ReportStatus.VERIFIED, verified_information={"conditions": ["asthma"]})
        db.add(report)
        db.commit()
        report_id = str(report.id)

    monkeypatch.setattr("app.api.workflow.get_settings", lambda: type("Settings", (), {"report_storage_path": tmp_path})())
    doctor_login = client.post("/api/v1/auth/login", json={"email": doctor_email, "password": "SafeLocalPass_2026!"})
    doctor_headers = {"Authorization": f"Bearer {doctor_login.json()['access_token']}"}
    summary = client.get(f"/api/v1/doctor/patients/{patient_id}/reports", headers=doctor_headers)
    assert summary.status_code == 200
    assert summary.json()[0]["verified_information"] == {"conditions": ["asthma"]}
    download = client.get(f"/api/v1/doctor/reports/{report_id}/download", headers=doctor_headers)
    assert download.status_code == 200
    assert download.content == original

    other_login = client.post("/api/v1/auth/login", json={"email": other_doctor_email, "password": "SafeLocalPass_2026!"})
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}
    assert client.get(f"/api/v1/doctor/patients/{patient_id}/reports", headers=other_headers).status_code == 404
    assert client.get(f"/api/v1/doctor/reports/{report_id}/download", headers=other_headers).status_code == 404
    assert client.get(f"/api/v1/doctor/patients/{patient_id}/reports", headers=patient_headers).status_code == 403
