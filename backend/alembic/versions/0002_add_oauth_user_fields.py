"""Add OAuth profile fields to users

Revision ID: 0002_add_oauth_user_fields
Revises: 0001_initial_schema
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_add_oauth_user_fields"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("google_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("avatar_url", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.create_index(batch_op.f("ix_users_google_id"), ["google_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_google_id"))
        batch_op.drop_column("email_verified")
        batch_op.drop_column("avatar_url")
        batch_op.drop_column("google_id")
