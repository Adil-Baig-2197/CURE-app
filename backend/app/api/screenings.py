from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.api.patients import current_patient_profile
from app.db.models import AuditEvent, PatientProfile, Screening, User, UserRole
from app.db.session import get_db
from app.services.screenings import create_screening

router = APIRouter(prefix="/screenings", tags=["screenings"])


class ScreeningCreate(BaseModel):
    """Temporary persistence contract; questionnaire routes will supply validated structured responses."""

    responses: dict = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)


class ScreeningCreated(BaseModel):
    id: str
    medical_snapshot: dict
    prediction_available: bool = False


@router.post("", response_model=ScreeningCreated, status_code=status.HTTP_201_CREATED)
def create_my_screening(
    payload: ScreeningCreate,
    profile: PatientProfile = Depends(current_patient_profile),
    user: User = Depends(require_roles(UserRole.PATIENT)),
    db: Session = Depends(get_db),
) -> ScreeningCreated:
    screening = create_screening(db, profile, payload.responses, payload.missing_fields)
    db.flush()
    db.add(AuditEvent(actor_id=user.id, action="screening.create", resource_type="screening", resource_id=str(screening.id)))
    db.commit()
    return ScreeningCreated(id=str(screening.id), medical_snapshot=screening.medical_snapshot)


@router.get("/{screening_id}", response_model=ScreeningCreated)
def get_my_screening(
    screening_id: str,
    profile: PatientProfile = Depends(current_patient_profile),
    db: Session = Depends(get_db),
) -> ScreeningCreated:
    screening = db.scalar(select(Screening).where(Screening.id == screening_id, Screening.patient_id == profile.id))
    if screening is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screening not found")
    return ScreeningCreated(id=str(screening.id), medical_snapshot=screening.medical_snapshot)
