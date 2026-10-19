"""Persist generated artifact bytes in the database.

Revision ID: 20261020_0002
Revises: 20261019_0001
"""
from alembic import op
import sqlalchemy as sa

revision = "20261020_0002"
down_revision = "20261019_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("artifacts", sa.Column("data", sa.LargeBinary(), nullable=True))


def downgrade():
    op.drop_column("artifacts", "data")
