"""initial schema

Revision ID: 20261023_01
Revises:
Create Date: 2026-10-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261023_01"
down_revision = None
branch_labels = None
depends_on = None

user_role = sa.Enum("patient", "doctor", "triage_staff", "administrator", name="user_role")
urgency_level = sa.Enum("low", "medium", "high", name="urgency_level")
intake_status = sa.Enum("new", "intake_in_progress", "routed", "completed", name="intake_status")
review_status = sa.Enum("pending", "confirmed", "corrected", name="review_status")
report_status = sa.Enum("uploaded", "extraction_failed", "awaiting_verification", "verified", name="report_status")


def upgrade() -> None:
    op.create_table("users", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("email", sa.String(320), nullable=False, unique=True), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("role", user_role, nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])
    op.create_table("patient_profiles", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("date_of_birth", sa.String(10)), sa.Column("sex_at_birth", sa.String(64)), sa.Column("phone_number", sa.String(32)), sa.Column("no_reports_declared", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table("medical_histories", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False), sa.Column("conditions", sa.JSON(), nullable=False), sa.Column("medications", sa.JSON(), nullable=False), sa.Column("notes", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_medical_histories_patient_id", "medical_histories", ["patient_id"])
    op.create_table("doctor_patient_assignments", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("doctor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False), sa.Column("assigned_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("doctor_id", "patient_id", name="doctor_patient_assignment"))
    op.create_index("ix_doctor_patient_assignments_doctor_id", "doctor_patient_assignments", ["doctor_id"])
    op.create_index("ix_doctor_patient_assignments_patient_id", "doctor_patient_assignments", ["patient_id"])
    op.create_table("medical_reports", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False), sa.Column("original_filename", sa.String(255), nullable=False), sa.Column("storage_key", sa.String(512), nullable=False, unique=True), sa.Column("content_type", sa.String(128), nullable=False), sa.Column("byte_size", sa.Integer(), nullable=False), sa.Column("status", report_status, nullable=False), sa.Column("raw_extraction", sa.JSON()), sa.Column("verified_information", sa.JSON()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_medical_reports_patient_id", "medical_reports", ["patient_id"])
    op.create_table("model_versions", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("version", sa.String(80), nullable=False, unique=True), sa.Column("metadata_json", sa.JSON(), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table("screenings", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient_profiles.id", ondelete="RESTRICT"), nullable=False), sa.Column("responses", sa.JSON(), nullable=False), sa.Column("medical_snapshot", sa.JSON(), nullable=False), sa.Column("missing_fields", sa.JSON(), nullable=False), sa.Column("predicted_urgency", urgency_level), sa.Column("prediction_score", sa.Float()), sa.Column("explanation", sa.JSON()), sa.Column("emergency_warning", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("emergency_reasons", sa.JSON(), nullable=False), sa.Column("intake_status", intake_status, nullable=False, server_default="new"), sa.Column("model_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_versions.id", ondelete="SET NULL")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_screenings_patient_id", "screenings", ["patient_id"])
    op.create_index("ix_screenings_emergency_warning", "screenings", ["emergency_warning"])
    op.create_index("ix_screenings_intake_status", "screenings", ["intake_status"])
    op.create_table("screening_reviews", sa.Column("screening_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("screenings.id", ondelete="CASCADE"), primary_key=True), sa.Column("doctor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("status", review_status, nullable=False, server_default="pending"), sa.Column("corrected_urgency", urgency_level), sa.Column("correction_reason", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table("audit_events", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("action", sa.String(120), nullable=False), sa.Column("resource_type", sa.String(80), nullable=False), sa.Column("resource_id", sa.String(64)), sa.Column("details", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])


def downgrade() -> None:
    for table in ("audit_events", "screening_reviews", "screenings", "model_versions", "medical_reports", "doctor_patient_assignments", "medical_histories", "patient_profiles", "users"):
        op.drop_table(table)
    for enum_type in (report_status, review_status, intake_status, urgency_level, user_role):
        enum_type.drop(op.get_bind(), checkfirst=True)
