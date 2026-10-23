from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MedicalHistory, PatientProfile, Screening


def medical_snapshot(db: Session, profile: PatientProfile) -> dict:
    """Capture the known state now; `None` denotes unknown, never normal."""
    history = db.scalar(
        select(MedicalHistory)
        .where(MedicalHistory.patient_id == profile.id)
        .order_by(MedicalHistory.updated_at.desc())
    )
    return {
        "date_of_birth": profile.date_of_birth,
        "sex_at_birth": profile.sex_at_birth,
        "no_reports_declared": profile.no_reports_declared,
        "conditions": list(history.conditions) if history else None,
        "medications": list(history.medications) if history else None,
        "history_notes": history.notes if history else None,
    }


def create_screening(db: Session, profile: PatientProfile, responses: dict, missing_fields: list[str], emergency_reasons: list[str] | None = None) -> Screening:
    screening = Screening(
        patient_id=profile.id,
        responses=responses,
        missing_fields=missing_fields,
        medical_snapshot=medical_snapshot(db, profile),
        emergency_warning=bool(emergency_reasons),
        emergency_reasons=emergency_reasons or [],
    )
    db.add(screening)
    return screening
