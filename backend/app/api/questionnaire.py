from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import require_roles
from app.api.patients import current_patient_profile
from app.db.models import AuditEvent, PatientProfile, User, UserRole
from app.db.session import get_db
from app.services.emergency import evaluate
from app.services.screenings import create_screening

router = APIRouter(prefix="/questionnaire", tags=["questionnaire"])


class Question(BaseModel):
    id: str
    prompt: str
    required: bool
    options: list[str] | None = None


BASE = [
    Question(id="symptoms", prompt="Which symptoms are you experiencing?", required=True, options=["fever", "cough", "shortness_of_breath", "chest_pain", "abdominal_pain", "vomiting", "headache", "weakness", "other"]),
    Question(id="severity", prompt="How severe are the symptoms?", required=True, options=["mild", "moderate", "severe"]),
    Question(id="duration", prompt="When did the symptoms begin?", required=True),
    Question(id="progression", prompt="Are symptoms improving, stable, or worsening?", required=True, options=["improving", "stable", "worsening"]),
    Question(id="free_text", prompt="Describe anything else that is important.", required=False),
]
FOLLOW_UPS = {"shortness_of_breath": Question(id="breath_at_rest", prompt="Does it occur while resting?", required=True, options=["yes", "no", "unknown"]), "chest_pain": Question(id="chest_pain_character", prompt="Describe the chest pain.", required=True, options=["pressure", "sharp", "burning", "other", "unknown"]), "abdominal_pain": Question(id="abdominal_location", prompt="Where is the pain located?", required=True), "headache": Question(id="headache_onset", prompt="Was it sudden or gradual?", required=True, options=["sudden", "gradual", "unknown"]), "weakness": Question(id="weakness_side", prompt="Is weakness on one side?", required=True, options=["yes", "no", "unknown"])}
EMERGENCY_QUESTIONS = [Question(id="severe_breathing_difficulty", prompt="Are you gasping, choking, or unable to get words out because of breathing difficulty?", required=True, options=["yes", "no", "unknown"]), Question(id="chest_pressure_or_spreading", prompt="Do you have chest pressure/tightness or pain spreading to an arm, neck, jaw, back, or stomach?", required=True, options=["yes", "no", "unknown"]), Question(id="face_droop", prompt="Has one side of the face suddenly drooped?", required=True, options=["yes", "no", "unknown"]), Question(id="one_sided_weakness", prompt="Is there sudden weakness or numbness on one side?", required=True, options=["yes", "no", "unknown"]), Question(id="speech_difficulty", prompt="Is speech suddenly slurred, confused, or difficult?", required=True, options=["yes", "no", "unknown"]), Question(id="unresponsive", prompt="Is the person unresponsive?", required=True, options=["yes", "no", "unknown"])]


@router.get("/questions", response_model=list[Question])
def questions(selected: list[str] = Query(default=[])) -> list[Question]:
    return [*EMERGENCY_QUESTIONS, *BASE, *(FOLLOW_UPS[x] for x in selected if x in FOLLOW_UPS)]


class Submission(BaseModel):
    responses: dict


@router.post("/submit", status_code=status.HTTP_201_CREATED)
def submit(payload: Submission, profile: PatientProfile = Depends(current_patient_profile), user: User = Depends(require_roles(UserRole.PATIENT)), db: Session = Depends(get_db)) -> dict:
    expected = {question.id for question in EMERGENCY_QUESTIONS + BASE}
    expected.update(question.id for symptom, question in FOLLOW_UPS.items() if symptom in payload.responses.get("symptoms", []))
    missing = sorted(key for key in expected if payload.responses.get(key) in (None, "", [], "unknown"))
    normalized = {key: value == "yes" if key in {q.id for q in EMERGENCY_QUESTIONS} else value for key, value in payload.responses.items()}
    reasons = evaluate(normalized)
    screening = create_screening(db, profile, normalized, missing, reasons)
    db.flush(); db.add(AuditEvent(actor_id=user.id, action="questionnaire.submit", resource_type="screening", resource_id=str(screening.id))); db.commit()
    return {"screening_id": str(screening.id), "emergency_warning": bool(reasons), "emergency_reasons": reasons, "message": "Seek emergency help immediately if an emergency warning is shown. Do not wait for CURE or a clinician response." if reasons else "Screening recorded; no ML prediction is available yet."}
