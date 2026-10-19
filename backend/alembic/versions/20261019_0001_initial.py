"""Initial workflow execution schema.

Revision ID: 20261019_0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision="20261019_0001"
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("workflows",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("name",sa.String(length=160),nullable=False),
        sa.Column("goal",sa.Text(),nullable=False),
        sa.Column("definition",sa.JSON(),nullable=False),
        sa.Column("version",sa.Integer(),server_default="1",nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("workflow_runs",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("workflow_id",sa.Integer(),sa.ForeignKey("workflows.id"),nullable=False),
        sa.Column("status",sa.String(length=32),nullable=False),
        sa.Column("approved",sa.Boolean(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("started_at",sa.DateTime(timezone=True)),
        sa.Column("finished_at",sa.DateTime(timezone=True)),
        sa.Column("result",sa.JSON()),sa.Column("error",sa.Text()))
    op.create_index("ix_workflow_runs_status","workflow_runs",["status"])
    op.create_table("step_runs",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("run_id",sa.Integer(),sa.ForeignKey("workflow_runs.id"),nullable=False),
        sa.Column("key",sa.String(length=80),nullable=False),
        sa.Column("title",sa.String(length=200),nullable=False),
        sa.Column("tool",sa.String(length=80),nullable=False),
        sa.Column("status",sa.String(length=32),nullable=False),
        sa.Column("output",sa.JSON()),sa.Column("error",sa.Text()),
        sa.Column("started_at",sa.DateTime(timezone=True)),sa.Column("finished_at",sa.DateTime(timezone=True)))
    op.create_index("ix_step_runs_run_id","step_runs",["run_id"])
    op.create_table("artifacts",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("run_id",sa.Integer(),sa.ForeignKey("workflow_runs.id"),nullable=False),
        sa.Column("filename",sa.String(length=200),nullable=False),
        sa.Column("path",sa.Text(),nullable=False),
        sa.Column("content_type",sa.String(length=100),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_artifacts_run_id","artifacts",["run_id"])

def downgrade():
    op.drop_index("ix_artifacts_run_id",table_name="artifacts");op.drop_table("artifacts")
    op.drop_index("ix_step_runs_run_id",table_name="step_runs");op.drop_table("step_runs")
    op.drop_index("ix_workflow_runs_status",table_name="workflow_runs");op.drop_table("workflow_runs")
    op.drop_table("workflows")
