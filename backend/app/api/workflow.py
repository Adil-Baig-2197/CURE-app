from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.auth import require_roles
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import AuditEvent, DoctorPatientAssignment, IntakeStatus, MedicalReport, PatientProfile, ReportStatus, ReviewStatus, Screening, ScreeningReview, UrgencyLevel, User, UserRole
from app.db.session import get_db

router = APIRouter(tags=["clinical workflow"])


class AccountCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: UserRole


class AccountUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class RouteRequest(BaseModel):
    doctor_id: UUID


class ReviewRequest(BaseModel):
    status: ReviewStatus
    corrected_urgency: UrgencyLevel | None = None
    correction_reason: str | None = Field(default=None, max_length=2000)


@router.get("/admin/accounts")
def list_accounts(_: User = Depends(require_roles(UserRole.ADMINISTRATOR)), db: Session = Depends(get_db)) -> list[dict]:
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return [{"id": str(user.id), "email": user.email, "role": user.role.value, "is_active": user.is_active} for user in users]


@router.get("/admin/analytics")
def analytics(_: User = Depends(require_roles(UserRole.ADMINISTRATOR)), db: Session = Depends(get_db)) -> dict:
    def count(statement): return db.scalar(statement) or 0
    return {
        "accounts_by_role": {role.value: count(select(func.count()).select_from(User).where(User.role == role)) for role in UserRole},
        "screenings_total": count(select(func.count()).select_from(Screening)),
        "emergency_flagged": count(select(func.count()).select_from(Screening).where(Screening.emergency_warning.is_(True))),
        "routed_screenings": count(select(func.count()).select_from(Screening).where(Screening.intake_status == IntakeStatus.ROUTED)),
        "corrected_reviews": count(select(func.count()).select_from(ScreeningReview).where(ScreeningReview.status == ReviewStatus.CORRECTED)),
        "model_status": "No model deployed; metrics unavailable until authorized dataset evaluation.",
    }


@router.post("/admin/accounts")
def create_account(payload: AccountCreate, admin: User = Depends(require_roles(UserRole.ADMINISTRATOR)), db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(409, "An account already uses this email")
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password), role=payload.role)
    db.add(user); db.flush(); db.add(AuditEvent(actor_id=admin.id, action="admin.account.create", resource_type="user", resource_id=str(user.id), details={"role": user.role.value})); db.commit()
    return {"id": str(user.id), "email": user.email, "role": user.role.value}


@router.patch("/admin/accounts/{account_id}")
def update_account(account_id: UUID, payload: AccountUpdate, admin: User = Depends(require_roles(UserRole.ADMINISTRATOR)), db: Session = Depends(get_db)) -> dict:
    if payload.role is None and payload.is_active is None:
        raise HTTPException(422, "Provide a role or active-state change")
    account = db.get(User, account_id)
    if account is None:
        raise HTTPException(404, "Account not found")
    if account.id == admin.id and (payload.is_active is False or (payload.role is not None and payload.role != UserRole.ADMINISTRATOR)):
        raise HTTPException(409, "Administrators cannot remove their own administrative access")
    removing_admin_privilege = account.is_active and account.role == UserRole.ADMINISTRATOR and (
        payload.is_active is False or (payload.role is not None and payload.role != UserRole.ADMINISTRATOR)
    )
    if removing_admin_privilege:
        active_admins = db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.ADMINISTRATOR, User.is_active.is_(True))) or 0
        if active_admins <= 1:
            raise HTTPException(409, "At least one active administrator must remain")
    before = {"role": account.role.value, "is_active": account.is_active}
    if payload.role is not None:
        account.role = payload.role
    if payload.is_active is not None:
        account.is_active = payload.is_active
    db.add(AuditEvent(actor_id=admin.id, action="admin.account.update", resource_type="user", resource_id=str(account.id), details={"before": before, "after": {"role": account.role.value, "is_active": account.is_active}}))
    db.commit()
    return {"id": str(account.id), "email": account.email, "role": account.role.value, "is_active": account.is_active}


@router.get("/triage/queue")
def triage_queue(_: User = Depends(require_roles(UserRole.TRIAGE_STAFF)), db: Session = Depends(get_db)) -> list[dict]:
    items = db.scalars(select(Screening).where(Screening.intake_status != IntakeStatus.COMPLETED).order_by(Screening.emergency_warning.desc(), Screening.predicted_urgency.desc().nulls_last(), Screening.created_at.asc())).all()
    return [{"id": str(item.id), "patient_id": str(item.patient_id), "emergency_warning": item.emergency_warning, "emergency_reasons": item.emergency_reasons, "predicted_urgency": item.predicted_urgency, "intake_status": item.intake_status} for item in items]


@router.post("/triage/screenings/{screening_id}/route")
def route_screening(screening_id: UUID, payload: RouteRequest, staff: User = Depends(require_roles(UserRole.TRIAGE_STAFF)), db: Session = Depends(get_db)) -> dict:
    screening = db.get(Screening, screening_id)
    doctor = db.get(User, payload.doctor_id)
    if screening is None or doctor is None or doctor.role != UserRole.DOCTOR:
        raise HTTPException(404, "Screening or doctor not found")
    assignment = db.scalar(select(DoctorPatientAssignment).where(DoctorPatientAssignment.doctor_id == doctor.id, DoctorPatientAssignment.patient_id == screening.patient_id))
    if assignment is None: db.add(DoctorPatientAssignment(doctor_id=doctor.id, patient_id=screening.patient_id, assigned_by_id=staff.id))
    screening.intake_status = IntakeStatus.ROUTED
    db.add(AuditEvent(actor_id=staff.id, action="triage.route", resource_type="screening", resource_id=str(screening.id), details={"doctor_id": str(doctor.id)})); db.commit()
    return {"screening_id": str(screening.id), "intake_status": screening.intake_status, "doctor_id": str(doctor.id)}


@router.get("/doctor/screenings")
def doctor_screenings(doctor: User = Depends(require_roles(UserRole.DOCTOR)), db: Session = Depends(get_db)) -> list[dict]:
    items = db.scalars(select(Screening).join(DoctorPatientAssignment, DoctorPatientAssignment.patient_id == Screening.patient_id).where(DoctorPatientAssignment.doctor_id == doctor.id).order_by(Screening.emergency_warning.desc(), Screening.predicted_urgency.desc().nulls_last(), Screening.created_at.asc())).all()
    return [{"id": str(item.id), "patient_id": str(item.patient_id), "responses": item.responses, "medical_snapshot": item.medical_snapshot, "emergency_warning": item.emergency_warning, "emergency_reasons": item.emergency_reasons, "predicted_urgency": item.predicted_urgency, "review_status": (db.get(ScreeningReview, item.id).status if db.get(ScreeningReview, item.id) else ReviewStatus.PENDING)} for item in items]


@router.post("/doctor/screenings/{screening_id}/review")
def review_screening(screening_id: UUID, payload: ReviewRequest, doctor: User = Depends(require_roles(UserRole.DOCTOR)), db: Session = Depends(get_db)) -> dict:
    screening = db.get(Screening, screening_id)
    if screening is None or db.scalar(select(DoctorPatientAssignment).where(DoctorPatientAssignment.doctor_id == doctor.id, DoctorPatientAssignment.patient_id == screening.patient_id)) is None:
        raise HTTPException(404, "Assigned screening not found")
    if payload.status == ReviewStatus.CORRECTED and (payload.corrected_urgency is None or not payload.correction_reason):
        raise HTTPException(422, "A corrected urgency and reason are required")
    review = db.get(ScreeningReview, screening_id) or ScreeningReview(screening_id=screening_id, doctor_id=doctor.id)
    review.status, review.corrected_urgency, review.correction_reason = payload.status, payload.corrected_urgency, payload.correction_reason
    db.add(review); db.add(AuditEvent(actor_id=doctor.id, action="doctor.review", resource_type="screening", resource_id=str(screening_id), details={"status": payload.status.value, "original_prediction": screening.predicted_urgency.value if screening.predicted_urgency else None, "corrected_urgency": payload.corrected_urgency.value if payload.corrected_urgency else None, "correction_reason": payload.correction_reason if payload.status == ReviewStatus.CORRECTED else None})); db.commit()
    return {"screening_id": str(screening_id), "status": review.status, "corrected_urgency": review.corrected_urgency}


class IntakeStatusUpdate(BaseModel):
    status: IntakeStatus


@router.patch("/triage/screenings/{screening_id}/status")
def update_intake_status(
    screening_id: UUID,
    payload: IntakeStatusUpdate,
    staff: User = Depends(require_roles(UserRole.TRIAGE_STAFF)),
    db: Session = Depends(get_db),
) -> dict:
    if payload.status == IntakeStatus.ROUTED:
        raise HTTPException(422, "Use the route action to assign a doctor before marking a screening routed")
    screening = db.get(Screening, screening_id)
    if screening is None:
        raise HTTPException(404, "Screening not found")
    screening.intake_status = payload.status
    db.add(AuditEvent(actor_id=staff.id, action="triage.status.update", resource_type="screening", resource_id=str(screening.id), details={"status": payload.status.value}))
    db.commit()
    return {"screening_id": str(screening.id), "intake_status": screening.intake_status}


@router.get("/doctor/patients/{patient_id}/reports")
def assigned_patient_report_summaries(
    patient_id: UUID,
    doctor: User = Depends(require_roles(UserRole.DOCTOR)),
    db: Session = Depends(get_db),
) -> list[dict]:
    assigned = db.scalar(select(DoctorPatientAssignment.id).where(DoctorPatientAssignment.doctor_id == doctor.id, DoctorPatientAssignment.patient_id == patient_id))
    if assigned is None:
        raise HTTPException(404, "Assigned patient not found")
    reports = db.scalars(select(MedicalReport).where(MedicalReport.patient_id == patient_id, MedicalReport.status == ReportStatus.VERIFIED).order_by(MedicalReport.created_at.desc())).all()
    db.add(AuditEvent(actor_id=doctor.id, action="doctor.report_summary.view", resource_type="patient_profile", resource_id=str(patient_id)))
    db.commit()
    return [{"id": str(report.id), "original_filename": report.original_filename, "created_at": report.created_at, "verified_information": report.verified_information, "download_path": f"/doctor/reports/{report.id}/download"} for report in reports]


@router.get("/doctor/reports/{report_id}/download")
def download_assigned_patient_report(
    report_id: UUID,
    doctor: User = Depends(require_roles(UserRole.DOCTOR)),
    db: Session = Depends(get_db),
) -> FileResponse:
    report = db.get(MedicalReport, report_id)
    if report is None:
        raise HTTPException(404, "Report not found")
    assigned = db.scalar(select(DoctorPatientAssignment.id).where(DoctorPatientAssignment.doctor_id == doctor.id, DoctorPatientAssignment.patient_id == report.patient_id))
    if assigned is None:
        raise HTTPException(404, "Report not found")
    root = get_settings().report_storage_path.resolve()
    path = (root / report.storage_key).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(404, "Report not found")
    db.add(AuditEvent(actor_id=doctor.id, action="doctor.report.download", resource_type="medical_report", resource_id=str(report.id)))
    db.commit()
    return FileResponse(path, media_type=report.content_type, filename=report.original_filename, content_disposition_type="attachment")
