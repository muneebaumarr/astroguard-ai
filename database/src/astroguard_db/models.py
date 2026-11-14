"""SQLAlchemy ORM tables. Internal to astroguard_db: repositories never return these."""
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON, Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index,
    Integer, String, Text, UniqueConstraint, text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

UUID_LEN = 36
SHORT = 200
ENUM_LEN = 40


class UTCDateTime(TypeDecorator):
    """Stores UTC without tzinfo (SQLite has no timezone type); returns aware UTC values."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("naive timestamps are not accepted; use timezone-aware UTC")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


class Base(DeclarativeBase):
    pass


class MissionRow(Base):
    __tablename__ = "missions"
    __table_args__ = (
        CheckConstraint("ended_at IS NULL OR ended_at > started_at", name="ck_missions_chronological"),
    )

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    name: Mapped[str] = mapped_column(String(SHORT), nullable=False)
    environment: Mapped[str] = mapped_column(String(ENUM_LEN), nullable=False)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AstronautRow(Base):
    __tablename__ = "astronauts"
    __table_args__ = (Index("ix_astronauts_mission_id", "mission_id"),)

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    mission_id: Mapped[str] = mapped_column(String(UUID_LEN), ForeignKey("missions.id", ondelete="RESTRICT"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(SHORT), nullable=False)
    role: Mapped[str] = mapped_column(String(SHORT), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CheckinRow(Base):
    """Vital values are NOT stored here; they live in health_readings (checkin_id)."""

    __tablename__ = "daily_checkins"
    __table_args__ = (
        UniqueConstraint("astronaut_id", "checkin_date", name="uq_daily_checkins_astronaut_date"),
        Index("ix_daily_checkins_astronaut_observed", "astronaut_id", "observed_at"),
    )

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    astronaut_id: Mapped[str] = mapped_column(String(UUID_LEN), ForeignKey("astronauts.id", ondelete="RESTRICT"), nullable=False)
    checkin_date: Mapped[date] = mapped_column(Date, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    context: Mapped[str] = mapped_column(String(ENUM_LEN), nullable=False)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    mood: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    symptoms: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    exercise_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class SimulationRunRow(Base):
    """active_slot is 1 for paused/running runs and NULL otherwise.
    Its unique constraint allows only one active run globally (SQLite treats NULLs as distinct)."""

    __tablename__ = "simulation_runs"
    __table_args__ = (UniqueConstraint("active_slot", name="uq_simulation_runs_active_slot"),)

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    astronaut_id: Mapped[str] = mapped_column(String(UUID_LEN), ForeignKey("astronauts.id", ondelete="RESTRICT"), nullable=False)
    mission_id: Mapped[str] = mapped_column(String(UUID_LEN), ForeignKey("missions.id", ondelete="RESTRICT"), nullable=False)
    scenario: Mapped[str] = mapped_column(String(ENUM_LEN), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    simulation_start_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    step_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario_version: Mapped[str] = mapped_column(String(SHORT), nullable=False)
    status: Mapped[str] = mapped_column(String(ENUM_LEN), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    last_tick_index: Mapped[int] = mapped_column(Integer, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    active_slot: Mapped[int | None] = mapped_column(Integer, nullable=True)


class HealthReadingRow(Base):
    __tablename__ = "health_readings"
    __table_args__ = (
        Index("ix_health_readings_history", "astronaut_id", "indicator", "observed_at", "id"),
        Index("ix_health_readings_checkin_id", "checkin_id"),
        UniqueConstraint("simulation_run_id", "tick_index", "indicator", name="uq_health_readings_run_tick_indicator"),
    )

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    astronaut_id: Mapped[str] = mapped_column(String(UUID_LEN), ForeignKey("astronauts.id", ondelete="RESTRICT"), nullable=False)
    indicator: Mapped[str] = mapped_column(String(ENUM_LEN), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(ENUM_LEN), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    source: Mapped[str] = mapped_column(String(ENUM_LEN), nullable=False)
    context: Mapped[str] = mapped_column(String(ENUM_LEN), nullable=False)
    checkin_id: Mapped[str | None] = mapped_column(String(UUID_LEN), ForeignKey("daily_checkins.id", ondelete="RESTRICT"), nullable=True)
    simulation_run_id: Mapped[str | None] = mapped_column(String(UUID_LEN), ForeignKey("simulation_runs.id", ondelete="RESTRICT"), nullable=True)
    tick_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EnvironmentalReadingRow(Base):
    __tablename__ = "environmental_readings"
    __table_args__ = (
        Index("ix_environmental_readings_history", "mission_id", "indicator", "observed_at", "id"),
        UniqueConstraint("simulation_run_id", "tick_index", "indicator", name="uq_environmental_readings_run_tick_indicator"),
    )

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    mission_id: Mapped[str] = mapped_column(String(UUID_LEN), ForeignKey("missions.id", ondelete="RESTRICT"), nullable=False)
    indicator: Mapped[str] = mapped_column(String(ENUM_LEN), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(ENUM_LEN), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    source: Mapped[str] = mapped_column(String(ENUM_LEN), nullable=False)
    simulation_run_id: Mapped[str] = mapped_column(String(UUID_LEN), ForeignKey("simulation_runs.id", ondelete="RESTRICT"), nullable=False)
    tick_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AssessmentRow(Base):
    __tablename__ = "assessments"
    __table_args__ = (
        UniqueConstraint("astronaut_id", "ruleset_version", "input_fingerprint", name="uq_assessments_fingerprint"),
        Index("ix_assessments_astronaut_evaluated", "astronaut_id", "evaluated_at"),
    )

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    astronaut_id: Mapped[str] = mapped_column(String(UUID_LEN), ForeignKey("astronauts.id", ondelete="RESTRICT"), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    status: Mapped[str] = mapped_column(String(ENUM_LEN), nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String(SHORT), nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    coverage: Mapped[dict] = mapped_column(JSON, nullable=False)
    results: Mapped[list] = mapped_column(JSON, nullable=False)


class AlertRow(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_astronaut_state", "astronaut_id", "state"),
        Index(
            "uq_alerts_active_rule", "astronaut_id", "rule_id", unique=True,
            sqlite_where=text("state IN ('open', 'acknowledged')"),
        ),
    )

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    astronaut_id: Mapped[str] = mapped_column(String(UUID_LEN), ForeignKey("astronauts.id", ondelete="RESTRICT"), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(SHORT), nullable=False)
    workflow_status: Mapped[str] = mapped_column(String(ENUM_LEN), nullable=False)
    state: Mapped[str] = mapped_column(String(ENUM_LEN), nullable=False)
    first_assessment_id: Mapped[str] = mapped_column(String(UUID_LEN), ForeignKey("assessments.id", ondelete="RESTRICT"), nullable=False)
    latest_assessment_id: Mapped[str] = mapped_column(String(UUID_LEN), ForeignKey("assessments.id", ondelete="RESTRICT"), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class CommandReceiptRow(Base):
    __tablename__ = "command_receipts"

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    operation: Mapped[str] = mapped_column(String(SHORT), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_type: Mapped[str] = mapped_column(String(SHORT), nullable=False)
    result_id: Mapped[str] = mapped_column(String(UUID_LEN), nullable=False)


REQUIRED_TABLES = frozenset(Base.metadata.tables)
