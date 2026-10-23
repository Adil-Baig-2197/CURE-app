from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_roles
from app.api.patients import current_patient_profile
from app.core.config import get_settings
from app.db.models import AuditEvent, MedicalReport, PatientProfile, ReportStatus, User, UserRole
from app.db.session import get_db
from app.services.reports import ALLOWED_CONTENT_TYPES, extract_text, save_original, structured_candidates

router = APIRouter(prefix="/reports", tags=["medical reports"])


class ReportResponse(BaseModel):
    id: str
    original_filename: str
    status: ReportStatus
    raw_extraction: dict | None
    verified_information: dict | None


class VerificationRequest(BaseModel):
    verified_information: dict


@router.get("", response_model=list[ReportResponse])
def list_my_reports(
    profile: PatientProfile = Depends(current_patient_profile), db: Session = Depends(get_db)
) -> list[ReportResponse]:
    reports = db.scalars(select(MedicalReport).where(MedicalReport.patient_id == profile.id).order_by(MedicalReport.created_at.desc())).all()
    return [ReportResponse(id=str(report.id), original_filename=report.original_filename, status=report.status, raw_extraction=report.raw_extraction, verified_information=report.verified_information) for report in reports]


def patient_report(report_id: UUID, profile: PatientProfile, db: Session) -> MedicalReport:
    report = db.scalar(select(MedicalReport).where(MedicalReport.id == report_id, MedicalReport.patient_id == profile.id))
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def upload_report(
    upload: UploadFile = File(...), profile: PatientProfile = Depends(current_patient_profile), user: User = Depends(require_roles(UserRole.PATIENT)), db: Session = Depends(get_db)
) -> ReportResponse:
    settings = get_settings()
    if upload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Only PDF, JPG, and PNG reports are supported")
    content = await upload.read(settings.max_report_upload_bytes + 1)
    if not content or len(content) > settings.max_report_upload_bytes:
        raise HTTPException(status_code=413, detail="Report is empty or exceeds the configured upload limit")
    try:
        text, limitations = extract_text(content, upload.content_type)
    except Exception:
        raise HTTPException(status_code=422, detail="The report could not be read safely")
    raw = {"text": text, "candidates": structured_candidates(text), "limitations": limitations + ["Extracted information is unverified and must not be treated as confirmed medical history."]}
    report = MedicalReport(patient_id=profile.id, original_filename=Path(upload.filename or "report").name, storage_key=save_original(settings.report_storage_path, content, upload.content_type), content_type=upload.content_type, byte_size=len(content), status=ReportStatus.AWAITING_VERIFICATION, raw_extraction=raw)
    db.add(report); db.flush(); db.add(AuditEvent(actor_id=user.id, action="report.upload", resource_type="medical_report", resource_id=str(report.id))); db.commit()
    return ReportResponse(id=str(report.id), original_filename=report.original_filename, status=report.status, raw_extraction=raw, verified_information=None)


@router.put("/{report_id}/verification", response_model=ReportResponse)
def verify_report(report_id: UUID, payload: VerificationRequest, profile: PatientProfile = Depends(current_patient_profile), user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ReportResponse:
    report = patient_report(report_id, profile, db)
    report.verified_information = payload.verified_information; report.status = ReportStatus.VERIFIED
    db.add(AuditEvent(actor_id=user.id, action="report.verify", resource_type="medical_report", resource_id=str(report.id))); db.commit()
    return ReportResponse(id=str(report.id), original_filename=report.original_filename, status=report.status, raw_extraction=report.raw_extraction, verified_information=report.verified_information)
