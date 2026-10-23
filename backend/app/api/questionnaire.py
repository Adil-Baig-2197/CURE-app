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
    multiple: bool = False


BASE = [
    Question(id="symptoms", prompt="Which symptoms are you experiencing?", required=True, options=["fever", "cough", "shortness_of_breath", "chest_pain", "palpitations", "abdominal_pain", "nausea", "vomiting", "diarrhea", "headache", "dizziness", "fainting", "confusion", "weakness", "rash", "other"], multiple=True),
    Question(id="associated_symptoms", prompt="What other symptoms are occurring alongside these?", required=False, options=["fever", "chills", "sweating", "cough", "shortness_of_breath", "chest_pain", "palpitations", "nausea", "vomiting", "diarrhea", "headache", "dizziness", "fainting", "confusion", "weakness", "numbness", "rash", "swelling", "other"], multiple=True),
    Question(id="severity", prompt="How severe are the symptoms?", required=True, options=["mild", "moderate", "severe"]),
    Question(id="duration", prompt="When did the symptoms begin?", required=True),
    Question(id="progression", prompt="Are symptoms improving, stable, or worsening?", required=True, options=["improving", "stable", "worsening"]),
    Question(id="free_text", prompt="Describe anything else that is important.", required=False),
]
FOLLOW_UPS = {
    "shortness_of_breath": Question(id="breath_at_rest", prompt="Does it occur while resting?", required=True, options=["yes", "no", "unknown"]),
    "chest_pain": Question(id="chest_pain_character", prompt="Describe the chest pain.", required=True, options=["pressure", "sharp", "burning", "other", "unknown"]),
    "palpitations": Question(id="palpitations_new", prompt="Are the palpitations new or unusually severe?", required=True, options=["yes", "no", "unknown"]),
    "abdominal_pain": Question(id="abdominal_location", prompt="Where is the pain located?", required=True),
    "diarrhea": Question(id="diarrhea_blood", prompt="Have you noticed blood in the stool?", required=True, options=["yes", "no", "unknown"]),
    "headache": Question(id="headache_onset", prompt="Was it sudden or gradual?", required=True, options=["sudden", "gradual", "unknown"]),
    "dizziness": Question(id="dizziness_fainting", prompt="Have you fainted or nearly fainted?", required=True, options=["yes", "no", "unknown"]),
    "fainting": Question(id="fainting_recovered", prompt="Have you fully regained awareness?", required=True, options=["yes", "no", "unknown"]),
    "confusion": Question(id="confusion_sudden", prompt="Did the confusion begin suddenly?", required=True, options=["yes", "no", "unknown"]),
    "weakness": Question(id="weakness_side", prompt="Is weakness on one side?", required=True, options=["yes", "no", "unknown"]),
}
EMERGENCY_QUESTIONS = [Question(id="severe_breathing_difficulty", prompt="Are you gasping, choking, or unable to get words out because of breathing difficulty?", required=True, options=["yes", "no", "unknown"]), Question(id="blue_or_grey_skin", prompt="Are the lips or skin turning blue, grey, or unusually pale?", required=True, options=["yes", "no", "unknown"]), Question(id="chest_pressure_or_spreading", prompt="Do you have chest pressure/tightness or pain spreading to an arm, neck, jaw, back, or stomach?", required=True, options=["yes", "no", "unknown"]), Question(id="face_droop", prompt="Has one side of the face suddenly drooped?", required=True, options=["yes", "no", "unknown"]), Question(id="one_sided_weakness", prompt="Is there sudden weakness or numbness on one side?", required=True, options=["yes", "no", "unknown"]), Question(id="speech_difficulty", prompt="Is speech suddenly slurred, confused, or difficult?", required=True, options=["yes", "no", "unknown"]), Question(id="sudden_confusion", prompt="Have you suddenly become confused or had difficulty thinking clearly?", required=True, options=["yes", "no", "unknown"]), Question(id="unresponsive", prompt="Is the person unresponsive?", required=True, options=["yes", "no", "unknown"])]


@router.get("/questions", response_model=list[Question])
def questions(selected: list[str] = Query(default=[])) -> list[Question]:
    return [*EMERGENCY_QUESTIONS, *BASE, *(FOLLOW_UPS[x] for x in selected if x in FOLLOW_UPS)]


class Submission(BaseModel):
    responses: dict


@router.post("/submit", status_code=status.HTTP_201_CREATED)
def submit(payload: Submission, profile: PatientProfile = Depends(current_patient_profile), user: User = Depends(require_roles(UserRole.PATIENT)), db: Session = Depends(get_db)) -> dict:
    supplied_symptoms = payload.responses.get("symptoms", [])
    selected = supplied_symptoms if isinstance(supplied_symptoms, list) else []
    questions_to_answer = [*EMERGENCY_QUESTIONS, *BASE, *(FOLLOW_UPS[x] for x in selected if isinstance(x, str) and x in FOLLOW_UPS)]
    valid_ids = {question.id for question in questions_to_answer}
    normalized: dict[str, object] = {}
    for question in questions_to_answer:
        value = payload.responses.get(question.id)
        if question.multiple:
            if isinstance(value, list):
                normalized[question.id] = [item for item in value if isinstance(item, str) and item in (question.options or [])]
        elif question.options:
            if isinstance(value, str) and value in question.options:
                normalized[question.id] = value
        elif isinstance(value, str):
            normalized[question.id] = value[:5000]
    normalized["symptoms"] = [item for item in selected if isinstance(item, str) and item in (BASE[0].options or [])]
    if "associated_symptoms" not in normalized:
        normalized["associated_symptoms"] = []
    required_ids = {question.id for question in questions_to_answer if question.required}
    missing = sorted(key for key in required_ids if normalized.get(key) in (None, "", [], "unknown"))
    emergency_ids = {q.id for q in EMERGENCY_QUESTIONS}
    normalized = {key: value == "yes" if key in emergency_ids else value for key, value in normalized.items() if key in valid_ids}
    reasons = evaluate(normalized)
    screening = create_screening(db, profile, normalized, missing, reasons)
    db.flush(); db.add(AuditEvent(actor_id=user.id, action="questionnaire.submit", resource_type="screening", resource_id=str(screening.id))); db.commit()
    return {"screening_id": str(screening.id), "emergency_warning": bool(reasons), "emergency_reasons": reasons, "message": "Seek emergency help immediately if an emergency warning is shown. Do not wait for CURE or a clinician response." if reasons else "Screening recorded; no ML prediction is available yet."}
