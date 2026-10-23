from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.core.config import get_settings
from app.db.models import AuditEvent, MedicalHistory, MedicalReport, PatientProfile, Screening, User, UserRole
from app.db.session import get_db

router = APIRouter(prefix="/patients", tags=["patients"])


class ProfileResponse(BaseModel):
    date_of_birth: date | None
    sex_at_birth: str | None
    phone_number: str | None
    no_reports_declared: bool


class ProfileUpdate(ProfileResponse):
    sex_at_birth: str | None = Field(default=None, max_length=64)
    phone_number: str | None = Field(default=None, max_length=32)


class MedicalHistoryResponse(BaseModel):
    conditions: list[str]
    medications: list[str]
    notes: str | None


class MedicalHistoryUpdate(MedicalHistoryResponse):
    conditions: list[str] = Field(default_factory=list, max_length=100)
    medications: list[str] = Field(default_factory=list, max_length=100)
    notes: str | None = Field(default=None, max_length=5000)


class DeletionRequest(BaseModel):
    confirmation: str


def current_patient_profile(
    user: User = Depends(require_roles(UserRole.PATIENT)), db: Session = Depends(get_db)
) -> PatientProfile:
    profile = db.scalar(select(PatientProfile).where(PatientProfile.user_id == user.id))
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    return profile


@router.get("/me/profile", response_model=ProfileResponse)
def get_my_profile(profile: PatientProfile = Depends(current_patient_profile)) -> ProfileResponse:
    return ProfileResponse(
        date_of_birth=date.fromisoformat(profile.date_of_birth) if profile.date_of_birth else None,
        sex_at_birth=profile.sex_at_birth,
        phone_number=profile.phone_number,
        no_reports_declared=profile.no_reports_declared,
    )


@router.put("/me/profile", response_model=ProfileResponse)
def update_my_profile(
    payload: ProfileUpdate,
    profile: PatientProfile = Depends(current_patient_profile),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    profile.date_of_birth = payload.date_of_birth.isoformat() if payload.date_of_birth else None
    profile.sex_at_birth = payload.sex_at_birth
    profile.phone_number = payload.phone_number
    profile.no_reports_declared = payload.no_reports_declared
    db.add(AuditEvent(actor_id=user.id, action="patient.profile.update", resource_type="patient_profile", resource_id=str(profile.id)))
    db.commit()
    return get_my_profile(profile)


@router.get("/me/history", response_model=MedicalHistoryResponse)
def get_my_history(profile: PatientProfile = Depends(current_patient_profile), db: Session = Depends(get_db)) -> MedicalHistoryResponse:
    history = db.scalar(select(MedicalHistory).where(MedicalHistory.patient_id == profile.id).order_by(MedicalHistory.updated_at.desc()))
    if history is None:
        return MedicalHistoryResponse(conditions=[], medications=[], notes=None)
    return MedicalHistoryResponse(conditions=history.conditions, medications=history.medications, notes=history.notes)


@router.put("/me/history", response_model=MedicalHistoryResponse)
def update_my_history(
    payload: MedicalHistoryUpdate,
    profile: PatientProfile = Depends(current_patient_profile),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MedicalHistoryResponse:
    history = db.scalar(select(MedicalHistory).where(MedicalHistory.patient_id == profile.id).order_by(MedicalHistory.updated_at.desc()))
    if history is None:
        history = MedicalHistory(patient_id=profile.id)
        db.add(history)
    history.conditions = payload.conditions
    history.medications = payload.medications
    history.notes = payload.notes
    db.add(AuditEvent(actor_id=user.id, action="patient.history.update", resource_type="medical_history", resource_id=str(history.id)))
    db.commit()
    return MedicalHistoryResponse(conditions=history.conditions, medications=history.medications, notes=history.notes)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_eligible_data(
    payload: DeletionRequest,
    profile: PatientProfile = Depends(current_patient_profile),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete an eligible account; historical screenings deliberately require separate retention review."""
    if payload.confirmation != "DELETE_MY_DATA":
        raise HTTPException(status_code=422, detail="Confirmation must equal DELETE_MY_DATA")
    if db.scalar(select(Screening.id).where(Screening.patient_id == profile.id).limit(1)):
        raise HTTPException(status_code=409, detail="Deletion is not yet eligible because historical screening records require retention review")
    reports = db.scalars(select(MedicalReport).where(MedicalReport.patient_id == profile.id)).all()
    storage_root = get_settings().report_storage_path
    for report in reports:
        path = storage_root / report.storage_key
        if path.is_file(): path.unlink()
    db.add(AuditEvent(actor_id=user.id, action="patient.delete.request.completed", resource_type="user", resource_id=str(user.id)))
    db.flush()
    db.delete(user)
    db.commit()
