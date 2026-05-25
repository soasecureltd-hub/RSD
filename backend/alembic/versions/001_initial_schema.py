"""Initial schema: users, assessments, camera_health, ai_predictions

Revision ID: 001
Revises:
Create Date: 2026-05-20
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("facility_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("category_scores", sa.JSON(), nullable=True),
        sa.Column("contributions", sa.JSON(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("risk_level", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "camera_health",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("camera_id", sa.String(), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("health_score", sa.Float(), nullable=False),
        sa.Column("blur_score", sa.Float(), nullable=True),
        sa.Column("brightness", sa.Float(), nullable=True),
        sa.Column("contrast", sa.Float(), nullable=True),
        sa.Column("noise_level", sa.Float(), nullable=True),
        sa.Column("fps", sa.Float(), nullable=True),
        sa.Column("issues", sa.JSON(), nullable=True),
    )

    op.create_table(
        "ai_predictions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("assessment_id", sa.Integer(), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("input_features", sa.JSON(), nullable=False),
        sa.Column("unauthorized_access_prob", sa.Float(), nullable=True),
        sa.Column("insider_threat_prob", sa.Float(), nullable=True),
        sa.Column("emergency_failure_prob", sa.Float(), nullable=True),
        sa.Column("perimeter_breach_prob", sa.Float(), nullable=True),
        sa.Column("shap_values", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("ai_predictions")
    op.drop_table("camera_health")
    op.drop_table("assessments")
    op.drop_table("users")
