"""Initial AstroGuard schema: all 9 tables.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

UUID = 36
SHORT = 200
ENUM = 40


def _id():
    return sa.Column("id", sa.String(UUID), primary_key=True)


def _created():
    return sa.Column("created_at", sa.DateTime(), nullable=False)


def _demo():
    return sa.Column("is_demo", sa.Boolean(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "missions",
        _id(), _created(),
        sa.Column("name", sa.String(SHORT), nullable=False),
        sa.Column("environment", sa.String(ENUM), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        _demo(),
        sa.CheckConstraint("ended_at IS NULL OR ended_at > started_at", name="ck_missions_chronological"),
    )

    op.create_table(
        "astronauts",
        _id(), _created(),
        sa.Column("mission_id", sa.String(UUID), sa.ForeignKey("missions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("display_name", sa.String(SHORT), nullable=False),
        sa.Column("role", sa.String(SHORT), nullable=False),
        _demo(),
    )
    op.create_index("ix_astronauts_mission_id", "astronauts", ["mission_id"])

    op.create_table(
        "daily_checkins",
        _id(), _created(),
        sa.Column("astronaut_id", sa.String(UUID), sa.ForeignKey("astronauts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("checkin_date", sa.Date(), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("context", sa.String(ENUM), nullable=False),
        sa.Column("sleep_hours", sa.Float(), nullable=True),
        sa.Column("mood", sa.Integer(), nullable=True),
        sa.Column("stress", sa.Integer(), nullable=True),
        sa.Column("symptoms", sa.JSON(), nullable=False),
        sa.Column("exercise_minutes", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        _demo(),
        sa.UniqueConstraint("astronaut_id", "checkin_date", name="uq_daily_checkins_astronaut_date"),
    )
    op.create_index("ix_daily_checkins_astronaut_observed", "daily_checkins", ["astronaut_id", "observed_at"])

    op.create_table(
        "simulation_runs",
        _id(), _created(),
        sa.Column("astronaut_id", sa.String(UUID), sa.ForeignKey("astronauts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("mission_id", sa.String(UUID), sa.ForeignKey("missions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scenario", sa.String(ENUM), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("simulation_start_at", sa.DateTime(), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column("step_seconds", sa.Integer(), nullable=False),
        sa.Column("scenario_version", sa.String(SHORT), nullable=False),
        sa.Column("status", sa.String(ENUM), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("last_tick_index", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("active_slot", sa.Integer(), nullable=True),
        sa.UniqueConstraint("active_slot", name="uq_simulation_runs_active_slot"),
    )

    op.create_table(
        "health_readings",
        _id(), _created(),
        sa.Column("astronaut_id", sa.String(UUID), sa.ForeignKey("astronauts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("indicator", sa.String(ENUM), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(ENUM), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(ENUM), nullable=False),
        sa.Column("context", sa.String(ENUM), nullable=False),
        sa.Column("checkin_id", sa.String(UUID), sa.ForeignKey("daily_checkins.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("simulation_run_id", sa.String(UUID), sa.ForeignKey("simulation_runs.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("tick_index", sa.Integer(), nullable=True),
        _demo(),
        sa.UniqueConstraint("simulation_run_id", "tick_index", "indicator", name="uq_health_readings_run_tick_indicator"),
    )
    op.create_index("ix_health_readings_history", "health_readings", ["astronaut_id", "indicator", "observed_at", "id"])
    op.create_index("ix_health_readings_checkin_id", "health_readings", ["checkin_id"])

    op.create_table(
        "environmental_readings",
        _id(), _created(),
        sa.Column("mission_id", sa.String(UUID), sa.ForeignKey("missions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("indicator", sa.String(ENUM), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(ENUM), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(ENUM), nullable=False),
        sa.Column("simulation_run_id", sa.String(UUID), sa.ForeignKey("simulation_runs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tick_index", sa.Integer(), nullable=False),
        _demo(),
        sa.UniqueConstraint("simulation_run_id", "tick_index", "indicator", name="uq_environmental_readings_run_tick_indicator"),
    )
    op.create_index("ix_environmental_readings_history", "environmental_readings", ["mission_id", "indicator", "observed_at", "id"])

    op.create_table(
        "assessments",
        _id(), _created(),
        sa.Column("astronaut_id", sa.String(UUID), sa.ForeignKey("astronauts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(ENUM), nullable=False),
        sa.Column("ruleset_version", sa.String(SHORT), nullable=False),
        sa.Column("input_fingerprint", sa.String(64), nullable=False),
        sa.Column("coverage", sa.JSON(), nullable=False),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.UniqueConstraint("astronaut_id", "ruleset_version", "input_fingerprint", name="uq_assessments_fingerprint"),
    )
    op.create_index("ix_assessments_astronaut_evaluated", "assessments", ["astronaut_id", "evaluated_at"])

    op.create_table(
        "alerts",
        _id(), _created(),
        sa.Column("astronaut_id", sa.String(UUID), sa.ForeignKey("astronauts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("rule_id", sa.String(SHORT), nullable=False),
        sa.Column("workflow_status", sa.String(ENUM), nullable=False),
        sa.Column("state", sa.String(ENUM), nullable=False),
        sa.Column("first_assessment_id", sa.String(UUID), sa.ForeignKey("assessments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("latest_assessment_id", sa.String(UUID), sa.ForeignKey("assessments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("opened_at", sa.DateTime(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_alerts_astronaut_state", "alerts", ["astronaut_id", "state"])
    op.create_index("uq_alerts_active_rule", "alerts", ["astronaut_id", "rule_id"], unique=True,
                    sqlite_where=sa.text("state IN ('open', 'acknowledged')"))

    op.create_table(
        "command_receipts",
        _id(), _created(),
        sa.Column("operation", sa.String(SHORT), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("result_type", sa.String(SHORT), nullable=False),
        sa.Column("result_id", sa.String(UUID), nullable=False),
    )


def downgrade() -> None:
    for table in ("command_receipts", "alerts", "assessments", "environmental_readings",
                  "health_readings", "simulation_runs", "daily_checkins", "astronauts", "missions"):
        op.drop_table(table)
