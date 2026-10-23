import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def enum_values(enum_class: type[enum.Enum]) -> list[str]:
    """Persist enum values (for example `patient`), never Python member names (`PATIENT`)."""
    return [member.value for member in enum_class]


class UserRole(str, enum.Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    TRIAGE_STAFF = "triage_staff"
    ADMINISTRATOR = "administrator"


class UrgencyLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IntakeStatus(str, enum.Enum):
    NEW = "new"
    INTAKE_IN_PROGRESS = "intake_in_progress"
    ROUTED = "routed"
    COMPLETED = "completed"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CORRECTED = "corrected"


class ReportStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    EXTRACTION_FAILED = "extraction_failed"
    AWAITING_VERIFICATION = "awaiting_verification"
    VERIFIED = "verified"


class TimestampedModel:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class User(TimestampedModel, Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role", values_callable=enum_values), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PatientProfile(TimestampedModel, Base):
    __tablename__ = "patient_profiles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    date_of_birth: Mapped[str | None] = mapped_column(String(10))
    sex_at_birth: Mapped[str | None] = mapped_column(String(64))
    phone_number: Mapped[str | None] = mapped_column(String(32))
    no_reports_declared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class MedicalHistory(TimestampedModel, Base):
    __tablename__ = "medical_histories"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    conditions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    medications: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class DoctorPatientAssignment(TimestampedModel, Base):
    __tablename__ = "doctor_patient_assignments"
    __table_args__ = (UniqueConstraint("doctor_id", "patient_id", name="doctor_patient_assignment"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class MedicalReport(TimestampedModel, Base):
    __tablename__ = "medical_reports"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus, name="report_status", values_callable=enum_values), nullable=False)
    raw_extraction: Mapped[dict | None] = mapped_column(JSON)
    verified_information: Mapped[dict | None] = mapped_column(JSON)


class ModelVersion(TimestampedModel, Base):
    __tablename__ = "model_versions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Screening(TimestampedModel, Base):
    __tablename__ = "screenings"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient_profiles.id", ondelete="RESTRICT"), nullable=False, index=True)
    responses: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    medical_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    missing_fields: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    predicted_urgency: Mapped[UrgencyLevel | None] = mapped_column(Enum(UrgencyLevel, name="urgency_level", values_callable=enum_values))
    prediction_score: Mapped[float | None] = mapped_column()
    explanation: Mapped[dict | None] = mapped_column(JSON)
    emergency_warning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    emergency_reasons: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    intake_status: Mapped[IntakeStatus] = mapped_column(Enum(IntakeStatus, name="intake_status", values_callable=enum_values), default=IntakeStatus.NEW, nullable=False, index=True)
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("model_versions.id", ondelete="SET NULL"))


class ScreeningReview(TimestampedModel, Base):
    __tablename__ = "screening_reviews"
    screening_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("screenings.id", ondelete="CASCADE"), primary_key=True)
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus, name="review_status", values_callable=enum_values), default=ReviewStatus.PENDING, nullable=False)
    corrected_urgency: Mapped[UrgencyLevel | None] = mapped_column(Enum(UrgencyLevel, name="urgency_level", values_callable=enum_values))
    correction_reason: Mapped[str | None] = mapped_column(Text)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
