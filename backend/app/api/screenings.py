from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.api.patients import current_patient_profile
from app.db.models import AuditEvent, IntakeStatus, PatientProfile, ReviewStatus, Screening, ScreeningReview, User, UserRole, UrgencyLevel
from app.db.session import get_db
from app.services.screenings import create_screening

router = APIRouter(prefix="/screenings", tags=["screenings"])


class ScreeningCreate(BaseModel):
    """Persistence contract; questionnaire routes supply validated structured responses."""

    responses: dict = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)


class ScreeningResponse(BaseModel):
    id: str
    created_at: datetime
    responses: dict
    missing_fields: list[str]
    medical_snapshot: dict
    predicted_urgency: UrgencyLevel | None
    prediction_score: float | None
    explanation: dict | None
    emergency_warning: bool
    emergency_reasons: list[str]
    intake_status: IntakeStatus
    review_status: ReviewStatus | None


@router.post("", response_model=ScreeningResponse, status_code=status.HTTP_201_CREATED)
def create_my_screening(
    payload: ScreeningCreate,
    profile: PatientProfile = Depends(current_patient_profile),
    user: User = Depends(require_roles(UserRole.PATIENT)),
    db: Session = Depends(get_db),
) -> ScreeningResponse:
    screening = create_screening(db, profile, payload.responses, payload.missing_fields)
    db.flush()
    db.add(AuditEvent(actor_id=user.id, action="screening.create", resource_type="screening", resource_id=str(screening.id)))
    db.commit()
    return _response(screening, None)


def _response(screening: Screening, review_status: ReviewStatus | None) -> ScreeningResponse:
    return ScreeningResponse(
        id=str(screening.id), created_at=screening.created_at, responses=screening.responses,
        missing_fields=screening.missing_fields, medical_snapshot=screening.medical_snapshot,
        predicted_urgency=screening.predicted_urgency, prediction_score=screening.prediction_score,
        explanation=screening.explanation, emergency_warning=screening.emergency_warning,
        emergency_reasons=screening.emergency_reasons, intake_status=screening.intake_status,
        review_status=review_status,
    )


@router.get("", response_model=list[ScreeningResponse])
def list_my_screenings(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: PatientProfile = Depends(current_patient_profile),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ScreeningResponse]:
    rows = db.execute(
        select(Screening, ScreeningReview.status)
        .outerjoin(ScreeningReview, ScreeningReview.screening_id == Screening.id)
        .where(Screening.patient_id == profile.id)
        .order_by(Screening.created_at.desc(), Screening.id.desc())
        .limit(limit).offset(offset)
    ).all()
    db.add(AuditEvent(actor_id=user.id, action="screening.history.view", resource_type="patient_profile", resource_id=str(profile.id), details={"limit": limit, "offset": offset}))
    db.commit()
    return [_response(screening, review_status) for screening, review_status in rows]


@router.get("/{screening_id}", response_model=ScreeningResponse)
def get_my_screening(
    screening_id: UUID,
    profile: PatientProfile = Depends(current_patient_profile),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScreeningResponse:
    row = db.execute(
        select(Screening, ScreeningReview.status)
        .outerjoin(ScreeningReview, ScreeningReview.screening_id == Screening.id)
        .where(Screening.id == screening_id, Screening.patient_id == profile.id)
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screening not found")
    screening, review_status = row
    db.add(AuditEvent(actor_id=user.id, action="screening.history.view", resource_type="screening", resource_id=str(screening.id)))
    db.commit()
    return _response(screening, review_status)
