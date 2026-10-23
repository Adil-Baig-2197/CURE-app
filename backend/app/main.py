from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.patients import router as patients_router
from app.api.screenings import router as screenings_router
from app.api.reports import router as reports_router
from app.api.questionnaire import router as questionnaire_router
from app.api.workflow import router as workflow_router

app = FastAPI(
    title="CURE API",
    version="0.1.0",
    description=(
        "Academic Clinical Urgency & Risk Evaluation prototype. "
        "It is not a diagnostic system or a clinically validated medical device."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(patients_router, prefix="/api/v1")
app.include_router(screenings_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(questionnaire_router, prefix="/api/v1")
app.include_router(workflow_router, prefix="/api/v1")
