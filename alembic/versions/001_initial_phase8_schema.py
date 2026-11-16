"""initial phase 8 saas schema

Revision ID: 001_initial_phase8_schema
Revises: 
Create Date: 2026-11-16 19:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_initial_phase8_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tenants Table
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("contact_email", sa.String(length=128), nullable=False),
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_tenants_slug", "tenants", ["slug"], unique=True)
    op.create_index("idx_tenants_status", "tenants", ["status"])

    # 2. Users Table
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("email", sa.String(length=128), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="TENANT_OPERATOR"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("mfa_secret", sa.String(length=64), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True)
    op.create_index("idx_users_tenant_id", "users", ["tenant_id"])

    # 3. Subscriptions Table
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_name", sa.String(length=32), nullable=False, server_default="TRIAL"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=False),
        sa.Column("grace_period_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("max_families", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("max_users", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_subscriptions_tenant_id", "subscriptions", ["tenant_id"])
    op.create_index("idx_subscriptions_status", "subscriptions", ["status"])

    # 4. Families Table
    op.create_table(
        "families",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("family_id_str", sa.String(length=64), nullable=False),
        sa.Column("head_name", sa.String(length=128), nullable=False),
        sa.Column("contact_number", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=128), nullable=True),
        sa.Column("city", sa.String(length=64), nullable=True),
        sa.Column("state", sa.String(length=64), nullable=True),
        sa.Column("preferred_date", sa.String(length=16), nullable=True),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="Normal"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="Pending"),
        sa.Column("donation_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("payment_status", sa.String(length=32), nullable=False, server_default="Pending"),
        sa.Column("payment_reference", sa.String(length=128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("desktop_source_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_families_tenant_status", "families", ["tenant_id", "status"])
    op.create_index("idx_families_tenant_prefdate", "families", ["tenant_id", "preferred_date"])
    op.create_index("idx_families_tenant_family_id_str", "families", ["tenant_id", "family_id_str"], unique=True)

    # 5. Pilgrims Table
    op.create_table(
        "pilgrims",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("family_id", sa.String(length=36), sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("gender", sa.String(length=16), nullable=False),
        sa.Column("id_type", sa.String(length=32), nullable=False),
        sa.Column("id_number_masked", sa.String(length=64), nullable=False),
        sa.Column("id_number_encrypted", sa.String(length=255), nullable=True),
        sa.Column("photo_path", sa.String(length=255), nullable=True),
        sa.Column("desktop_source_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_pilgrims_tenant_family", "pilgrims", ["tenant_id", "family_id"])
    op.create_index("idx_pilgrims_tenant_name", "pilgrims", ["tenant_id", "name"])

    # 6. Ticket Files Table
    op.create_table(
        "ticket_files",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("family_id", sa.String(length=36), sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("safe_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False, server_default="application/pdf"),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("sha256_checksum", sa.String(length=64), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_tickets_tenant_family", "ticket_files", ["tenant_id", "family_id"])
    op.create_index("idx_tickets_tenant_checksum", "ticket_files", ["tenant_id", "sha256_checksum"])

    # 7. Audit Logs Table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("details_sanitized", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_audit_tenant_created", "audit_logs", ["tenant_id", "created_at"])
    op.create_index("idx_audit_action_created", "audit_logs", ["action", "created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("ticket_files")
    op.drop_table("pilgrims")
    op.drop_table("families")
    op.drop_table("subscriptions")
    op.drop_table("users")
    op.drop_table("tenants")
