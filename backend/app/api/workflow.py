from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.auth import require_roles
from app.core.security import hash_password
from app.db.models import AuditEvent, DoctorPatientAssignment, IntakeStatus, PatientProfile, ReviewStatus, Screening, ScreeningReview, UrgencyLevel, User, UserRole
from app.db.session import get_db

router = APIRouter(tags=["clinical workflow"])


class AccountCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: UserRole


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


@router.get("/triage/queue")
def triage_queue(_: User = Depends(require_roles(UserRole.TRIAGE_STAFF)), db: Session = Depends(get_db)) -> list[dict]:
    items = db.scalars(select(Screening).where(Screening.intake_status != IntakeStatus.COMPLETED).order_by(Screening.emergency_warning.desc(), Screening.created_at.asc())).all()
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
    items = db.scalars(select(Screening).join(DoctorPatientAssignment, DoctorPatientAssignment.patient_id == Screening.patient_id).where(DoctorPatientAssignment.doctor_id == doctor.id).order_by(Screening.emergency_warning.desc(), Screening.created_at.desc())).all()
    return [{"id": str(item.id), "patient_id": str(item.patient_id), "responses": item.responses, "medical_snapshot": item.medical_snapshot, "emergency_warning": item.emergency_warning, "emergency_reasons": item.emergency_reasons, "predicted_urgency": item.predicted_urgency} for item in items]


@router.post("/doctor/screenings/{screening_id}/review")
def review_screening(screening_id: UUID, payload: ReviewRequest, doctor: User = Depends(require_roles(UserRole.DOCTOR)), db: Session = Depends(get_db)) -> dict:
    screening = db.get(Screening, screening_id)
    if screening is None or db.scalar(select(DoctorPatientAssignment).where(DoctorPatientAssignment.doctor_id == doctor.id, DoctorPatientAssignment.patient_id == screening.patient_id)) is None:
        raise HTTPException(404, "Assigned screening not found")
    if payload.status == ReviewStatus.CORRECTED and (payload.corrected_urgency is None or not payload.correction_reason):
        raise HTTPException(422, "A corrected urgency and reason are required")
    review = db.get(ScreeningReview, screening_id) or ScreeningReview(screening_id=screening_id, doctor_id=doctor.id)
    review.status, review.corrected_urgency, review.correction_reason = payload.status, payload.corrected_urgency, payload.correction_reason
    db.add(review); db.add(AuditEvent(actor_id=doctor.id, action="doctor.review", resource_type="screening", resource_id=str(screening_id), details={"status": payload.status.value})); db.commit()
    return {"screening_id": str(screening_id), "status": review.status, "corrected_urgency": review.corrected_urgency}
