#!/usr/bin/env python3
"""
Context Store for Ultra Trainer

This module provides a persistent SQLite datastore for athlete profile,
goals, episodes (injury/fatigue logs), and conversation history.
"""

import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Enum, Float, Boolean, Date, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class EpisodeTopic(enum.Enum):
    """Enumeration for episode topics."""
    INJURY = "injury"
    FATIGUE = "fatigue"
    EFFORT = "effort"
    MOTIVATION = "motivation"
    SLEEP = "sleep"
    NUTRITION = "nutrition"
    STRESS = "stress"
    RECOVERY = "recovery"
    OTHER = "other"


class PhaseType(enum.Enum):
    """Koop-style training phases."""
    BASE = "base"
    SPECIFIC = "specific"
    RACE_SPECIFIC = "race_specific"
    TAPER = "taper"
    RECOVERY = "recovery"


class AthleteProfile(Base):
    """One-row source of truth for stable athlete attributes."""
    __tablename__ = 'athlete_profile'
    
    athlete_id = Column(Integer, primary_key=True, autoincrement=True)
    birth_year = Column(Integer)
    gender = Column(String(10))
    history_text = Column(Text)
    # Additional profile fields
    weight_kg = Column(Float)
    running_years = Column(Integer)
    preferred_terrain = Column(String(50))
    weekly_mileage_km = Column(Float)
    ultra_experience = Column(Integer, default=0)
    current_location = Column(String(255))
    default_location = Column(String(255))
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class Goal(Base):
    """Future-dated target events (can be multiple)."""
    __tablename__ = 'goals'
    
    goal_id = Column(Integer, primary_key=True, autoincrement=True)
    event_name = Column(String(255), nullable=False)
    distance_km = Column(Float)
    event_datetime = Column(DateTime(timezone=True))
    context_text = Column(Text)
    target_time_seconds = Column(Integer)
    race_priority = Column(String(1))  # "A", "B", "C" or NULL
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class Episode(Base):
    """Episodic states the runner logs (injury, fatigue, etc.)."""
    __tablename__ = 'episodes'
    
    episode_id = Column(Integer, primary_key=True, autoincrement=True)
    topic = Column(Enum(EpisodeTopic), nullable=False)
    severity = Column(Integer)  # 1-10 scale where applicable
    narrative_text = Column(Text, nullable=False)
    start_date = Column(DateTime(timezone=True), default=func.now())
    end_date = Column(DateTime(timezone=True))  # NULL for ongoing episodes
    created_at = Column(DateTime(timezone=True), default=func.now())


class ConvoHistory(Base):
    """Raw chat history for conversation context."""
    __tablename__ = 'convo_history'

    turn_id = Column(Integer, primary_key=True, autoincrement=True)
    speaker = Column(String(50), nullable=False)  # 'user' or 'agent'
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=func.now())


class ConversationSummary(Base):
    """Compacted conversation summaries for cross-session memory."""
    __tablename__ = 'conversation_summaries'

    summary_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), nullable=False, unique=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=False)
    summary_short = Column(Text, nullable=False)
    summary_long = Column(Text, nullable=False)
    turn_count = Column(Integer, default=0)


class TrainingPlan(Base):
    """High-level training plan anchored to an A-race."""
    __tablename__ = 'training_plans'

    plan_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    a_race_goal_id = Column(Integer, ForeignKey('goals.goal_id'))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class TrainingPhase(Base):
    """A phase within a training plan."""
    __tablename__ = 'training_phases'

    phase_id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey('training_plans.plan_id'), nullable=False)
    phase_type = Column(Enum(PhaseType), nullable=False)
    name = Column(String(255))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    target_weekly_km = Column(Float)
    target_weekly_vert_m = Column(Float)
    target_long_run_km = Column(Float)
    notes = Column(Text)
    order_index = Column(Integer, default=0)


class TrainingWeek(Base):
    """A single calendar week within a training plan."""
    __tablename__ = 'training_weeks'

    week_id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey('training_plans.plan_id'), nullable=False)
    phase_id = Column(Integer, ForeignKey('training_phases.phase_id'))
    week_number = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    target_km = Column(Float)
    target_vert_m = Column(Float)
    target_long_run_km = Column(Float)
    notes = Column(Text)


class ContextStore:
    """Data access layer for Ultra Trainer persistent memory."""
    
    def __init__(self, db_url: str = "sqlite:///ultra_trainer.db"):
        """Initialize the context store with database connection."""
        # Ensure the database directory exists
        if db_url.startswith("sqlite:///"):
            db_path = Path(db_url.replace("sqlite:///", ""))
            db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Handle database migrations
        self._migrate_database()
    
    def _migrate_database(self):
        """Handle database schema migrations."""
        migrations = [
            ("athlete_profile", "current_location", "ALTER TABLE athlete_profile ADD COLUMN current_location VARCHAR(255)"),
            ("athlete_profile", "default_location", "ALTER TABLE athlete_profile ADD COLUMN default_location VARCHAR(255)"),
            ("goals", "race_priority", "ALTER TABLE goals ADD COLUMN race_priority VARCHAR(1)"),
        ]
        try:
            with self.engine.connect() as conn:
                for table, column, alter_sql in migrations:
                    try:
                        conn.execute(text(f"SELECT {column} FROM {table} LIMIT 1"))
                    except Exception:
                        conn.execute(text(alter_sql))
                        conn.commit()
        except Exception:
            pass
    
    def _get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
    
    # ------ Profile Methods ------
    
    def upsert_profile(
        self, 
        *, 
        birth_year: Optional[int] = None,
        gender: Optional[str] = None,
        history: Optional[str] = None,
        weight_kg: Optional[float] = None,
        running_years: Optional[int] = None,
        preferred_terrain: Optional[str] = None,
        weekly_mileage_km: Optional[float] = None,
        ultra_experience: Optional[int] = None,
        current_location: Optional[str] = None,
        default_location: Optional[str] = None
    ) -> None:
        """Create or update athlete profile."""
        with self._get_session() as session:
            profile = session.query(AthleteProfile).first()
            
            if profile is None:
                # Create new profile
                profile = AthleteProfile()
                session.add(profile)
            
            # Update fields if provided
            if birth_year is not None:
                profile.birth_year = birth_year
            if gender is not None:
                profile.gender = gender
            if history is not None:
                profile.history_text = history
            if weight_kg is not None:
                profile.weight_kg = weight_kg
            if running_years is not None:
                profile.running_years = running_years
            if preferred_terrain is not None:
                profile.preferred_terrain = preferred_terrain
            if weekly_mileage_km is not None:
                profile.weekly_mileage_km = weekly_mileage_km
            if ultra_experience is not None:
                profile.ultra_experience = ultra_experience
            if current_location is not None:
                profile.current_location = current_location
            if default_location is not None:
                profile.default_location = default_location
            
            session.commit()
    
    def get_profile(self) -> Optional[Dict[str, Any]]:
        """Get current athlete profile."""
        with self._get_session() as session:
            profile = session.query(AthleteProfile).first()
            if profile is None:
                return None
            
            return {
                "athlete_id": profile.athlete_id,
                "birth_year": profile.birth_year,
                "gender": profile.gender,
                "history_text": profile.history_text,
                "weight_kg": profile.weight_kg,
                "running_years": profile.running_years,
                "preferred_terrain": profile.preferred_terrain,
                "weekly_mileage_km": profile.weekly_mileage_km,
                "ultra_experience": profile.ultra_experience,
                "current_location": profile.current_location,
                "default_location": profile.default_location,
                "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
            }
    
    # ------ Goal Methods ------
    
    def add_or_update_goal(
        self,
        goal_id: Optional[int] = None,
        event_name: Optional[str] = None,
        distance_km: Optional[float] = None,
        event_datetime: Optional[datetime] = None,
        context_text: Optional[str] = None,
        target_time_seconds: Optional[int] = None,
        race_priority: Optional[str] = None,
    ) -> int:
        """Add new goal or update existing goal. Returns goal_id."""
        with self._get_session() as session:
            if goal_id:
                goal = session.query(Goal).filter(Goal.goal_id == goal_id).first()
                if goal is None:
                    raise ValueError(f"Goal with ID {goal_id} not found")
            else:
                goal = Goal()
                session.add(goal)

            if event_name is not None:
                goal.event_name = event_name
            if distance_km is not None:
                goal.distance_km = distance_km
            if event_datetime is not None:
                goal.event_datetime = event_datetime
            if context_text is not None:
                goal.context_text = context_text
            if target_time_seconds is not None:
                goal.target_time_seconds = target_time_seconds
            if race_priority is not None:
                goal.race_priority = race_priority.upper()[:1]

            session.commit()
            session.refresh(goal)
            return goal.goal_id
    
    def get_active_goals(self) -> List[Dict[str, Any]]:
        """Get all active goals (future events)."""
        with self._get_session() as session:
            now = datetime.now(timezone.utc)
            goals = session.query(Goal).filter(
                (Goal.event_datetime.is_(None)) | (Goal.event_datetime > now)
            ).order_by(Goal.event_datetime.asc()).all()
            
            return [
                {
                    "goal_id": goal.goal_id,
                    "event_name": goal.event_name,
                    "distance_km": goal.distance_km,
                    "event_datetime": goal.event_datetime.isoformat() if goal.event_datetime else None,
                    "context_text": goal.context_text,
                    "target_time_seconds": goal.target_time_seconds,
                    "race_priority": goal.race_priority,
                    "created_at": goal.created_at.isoformat() if goal.created_at else None,
                    "updated_at": goal.updated_at.isoformat() if goal.updated_at else None
                }
                for goal in goals
            ]
    
    def remove_goal(self, goal_id: Optional[int] = None, event_name: Optional[str] = None) -> bool:
        """
        Remove a goal by ID or event name.
        Returns True if a goal was removed, False otherwise.
        """
        with self._get_session() as session:
            query = session.query(Goal)
            
            if goal_id is not None:
                goal = query.filter(Goal.goal_id == goal_id).first()
            elif event_name is not None:
                goal = query.filter(Goal.event_name == event_name).first()
            else:
                return False
            
            if goal:
                session.delete(goal)
                session.commit()
                return True
            return False
    
    # ------ Episode Methods ------
    
    def log_episode(
        self,
        topic: str,
        narrative: str,
        severity: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """Log a new episode (injury, fatigue, etc.). Returns episode_id."""
        with self._get_session() as session:
            # Convert string topic to enum
            try:
                topic_enum = EpisodeTopic(topic.lower())
            except ValueError:
                topic_enum = EpisodeTopic.OTHER
            
            episode = Episode(
                topic=topic_enum,
                narrative_text=narrative,
                severity=severity,
                start_date=start_date or datetime.now(timezone.utc),
                end_date=end_date
            )
            
            session.add(episode)
            session.commit()
            session.refresh(episode)
            return episode.episode_id
    
    def current_episodes(self, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get current (ongoing) episodes, optionally filtered by topic."""
        with self._get_session() as session:
            query = session.query(Episode).filter(Episode.end_date.is_(None))
            
            if topic:
                try:
                    topic_enum = EpisodeTopic(topic.lower())
                    query = query.filter(Episode.topic == topic_enum)
                except ValueError:
                    # If invalid topic, return empty list
                    return []
            
            episodes = query.order_by(Episode.start_date.desc()).all()
            
            return [
                {
                    "episode_id": episode.episode_id,
                    "topic": episode.topic.value,
                    "severity": episode.severity,
                    "narrative_text": episode.narrative_text,
                    "start_date": episode.start_date.isoformat() if episode.start_date else None,
                    "end_date": episode.end_date.isoformat() if episode.end_date else None,
                    "created_at": episode.created_at.isoformat() if episode.created_at else None
                }
                for episode in episodes
            ]
    
    def end_episode(self, episode_id: int, end_date: Optional[datetime] = None) -> bool:
        """Mark an episode as ended. Returns True if successful."""
        with self._get_session() as session:
            episode = session.query(Episode).filter(Episode.episode_id == episode_id).first()
            if episode is None:
                return False
            
            episode.end_date = end_date or datetime.now(timezone.utc)
            session.commit()
            return True
    
    def get_recent_episodes(self, days: int = 30, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get episodes from the last N days."""
        with self._get_session() as session:
            cutoff_date = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=days)
            
            query = session.query(Episode).filter(Episode.start_date >= cutoff_date)
            
            if topic:
                try:
                    topic_enum = EpisodeTopic(topic.lower())
                    query = query.filter(Episode.topic == topic_enum)
                except ValueError:
                    return []
            
            episodes = query.order_by(Episode.start_date.desc()).all()
            
            return [
                {
                    "episode_id": episode.episode_id,
                    "topic": episode.topic.value,
                    "severity": episode.severity,
                    "narrative_text": episode.narrative_text,
                    "start_date": episode.start_date.isoformat() if episode.start_date else None,
                    "end_date": episode.end_date.isoformat() if episode.end_date else None,
                    "created_at": episode.created_at.isoformat() if episode.created_at else None
                }
                for episode in episodes
            ]
    
    # ------ Conversation History Methods ------
    
    def add_convo_turn(self, speaker: str, text: str) -> int:
        """Add a conversation turn. Returns turn_id."""
        with self._get_session() as session:
            turn = ConvoHistory(speaker=speaker, text=text)
            session.add(turn)
            session.commit()
            session.refresh(turn)
            return turn.turn_id
    
    def last_n_turns(self, n: int = 50) -> List[Dict[str, Any]]:
        """Get the last N conversation turns."""
        with self._get_session() as session:
            turns = session.query(ConvoHistory).order_by(
                ConvoHistory.timestamp.desc()
            ).limit(n).all()
            
            # Reverse to get chronological order
            turns.reverse()
            
            return [
                {
                    "turn_id": turn.turn_id,
                    "speaker": turn.speaker,
                    "text": turn.text,
                    "timestamp": turn.timestamp.isoformat() if turn.timestamp else None
                }
                for turn in turns
            ]
    
    def clear_old_conversations(self, days_to_keep: int = 90) -> int:
        """Clear conversation history older than specified days. Returns count of deleted turns."""
        with self._get_session() as session:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            count = session.query(ConvoHistory).filter(
                ConvoHistory.timestamp < cutoff_date
            ).count()
            
            session.query(ConvoHistory).filter(
                ConvoHistory.timestamp < cutoff_date
            ).delete()
            
            session.commit()
            return count
    
    # ------ Conversation Summary Methods ------

    def save_conversation_summary(
        self,
        session_id: str,
        summary_short: str,
        summary_long: str,
        started_at: datetime,
        ended_at: datetime,
        turn_count: int = 0,
    ) -> int:
        """Save a compacted conversation summary. Returns summary_id."""
        with self._get_session() as session:
            summary = ConversationSummary(
                session_id=session_id,
                started_at=started_at,
                ended_at=ended_at,
                summary_short=summary_short,
                summary_long=summary_long,
                turn_count=turn_count,
            )
            session.add(summary)
            session.commit()
            session.refresh(summary)
            return summary.summary_id

    def get_conversation_history(self, max_entries: int = 10) -> str:
        """
        Get formatted conversation history with compaction.
        Returns short summaries for older sessions, long summary for the most recent.
        """
        with self._get_session() as session:
            summaries = (
                session.query(ConversationSummary)
                .order_by(ConversationSummary.started_at.asc())
                .limit(max_entries)
                .all()
            )

            if not summaries:
                return ""

            lines = ["Previous coaching sessions:"]
            for i, s in enumerate(summaries):
                ts = s.started_at.strftime("%Y-%m-%d %H:%M") if s.started_at else "unknown"
                is_latest = i == len(summaries) - 1
                if is_latest:
                    lines.append(f"[{ts}] ({s.turn_count} exchanges) [RECENT]\n{s.summary_long}")
                else:
                    lines.append(f"[{ts}] ({s.turn_count} exchanges) {s.summary_short}")

            return "\n".join(lines)

    # ------ Training Plan Methods ------

    def create_plan(self, name: str, a_race_goal_id: int) -> int:
        """Create a new training plan, deactivating any existing active plan."""
        with self._get_session() as session:
            session.query(TrainingPlan).filter(TrainingPlan.is_active == True).update(
                {"is_active": False}
            )
            plan = TrainingPlan(name=name, a_race_goal_id=a_race_goal_id, is_active=True)
            session.add(plan)
            session.commit()
            session.refresh(plan)
            return plan.plan_id

    def get_active_plan(self) -> Optional[Dict[str, Any]]:
        """Get the active training plan with all phases."""
        with self._get_session() as session:
            plan = session.query(TrainingPlan).filter(TrainingPlan.is_active == True).first()
            if plan is None:
                return None

            phases = (
                session.query(TrainingPhase)
                .filter(TrainingPhase.plan_id == plan.plan_id)
                .order_by(TrainingPhase.order_index.asc())
                .all()
            )

            today = datetime.now(timezone.utc).date()

            weeks = (
                session.query(TrainingWeek)
                .filter(TrainingWeek.plan_id == plan.plan_id)
                .order_by(TrainingWeek.week_number.asc())
                .all()
            )

            return {
                "plan_id": plan.plan_id,
                "name": plan.name,
                "a_race_goal_id": plan.a_race_goal_id,
                "created_at": plan.created_at.isoformat() if plan.created_at else None,
                "phases": [
                    {
                        "phase_id": p.phase_id,
                        "phase_type": p.phase_type.value,
                        "name": p.name,
                        "start_date": p.start_date.isoformat(),
                        "end_date": p.end_date.isoformat(),
                        "target_weekly_km": p.target_weekly_km,
                        "target_weekly_vert_m": p.target_weekly_vert_m,
                        "target_long_run_km": p.target_long_run_km,
                        "notes": p.notes,
                        "order_index": p.order_index,
                        "is_current": p.start_date <= today <= p.end_date,
                    }
                    for p in phases
                ],
                "weeks": [
                    {
                        "week_id": w.week_id,
                        "phase_id": w.phase_id,
                        "week_number": w.week_number,
                        "start_date": w.start_date.isoformat(),
                        "end_date": w.end_date.isoformat(),
                        "target_km": w.target_km,
                        "target_vert_m": w.target_vert_m,
                        "target_long_run_km": w.target_long_run_km,
                        "notes": w.notes,
                        "is_current": w.start_date <= today <= w.end_date,
                    }
                    for w in weeks
                ],
            }

    def add_phase(
        self,
        plan_id: int,
        phase_type: str,
        start_date: str,
        end_date: str,
        name: Optional[str] = None,
        target_weekly_km: Optional[float] = None,
        target_weekly_vert_m: Optional[float] = None,
        target_long_run_km: Optional[float] = None,
        notes: Optional[str] = None,
        order_index: Optional[int] = None,
    ) -> int:
        """Add a phase to a training plan. Returns phase_id."""
        from datetime import date as date_type
        with self._get_session() as session:
            try:
                pt = PhaseType(phase_type.lower())
            except ValueError:
                pt = PhaseType.BASE

            if order_index is None:
                max_idx = (
                    session.query(func.max(TrainingPhase.order_index))
                    .filter(TrainingPhase.plan_id == plan_id)
                    .scalar()
                )
                order_index = (max_idx or 0) + 1

            phase = TrainingPhase(
                plan_id=plan_id,
                phase_type=pt,
                name=name,
                start_date=date_type.fromisoformat(start_date),
                end_date=date_type.fromisoformat(end_date),
                target_weekly_km=target_weekly_km,
                target_weekly_vert_m=target_weekly_vert_m,
                target_long_run_km=target_long_run_km,
                notes=notes,
                order_index=order_index,
            )
            session.add(phase)
            session.commit()
            session.refresh(phase)
            return phase.phase_id

    def update_phase(self, phase_id: int, **kwargs) -> bool:
        """Update fields on an existing phase."""
        from datetime import date as date_type
        with self._get_session() as session:
            phase = session.query(TrainingPhase).filter(TrainingPhase.phase_id == phase_id).first()
            if phase is None:
                return False

            for key, val in kwargs.items():
                if val is None:
                    continue
                if key == "phase_type":
                    try:
                        val = PhaseType(val.lower())
                    except ValueError:
                        continue
                if key in ("start_date", "end_date") and isinstance(val, str):
                    val = date_type.fromisoformat(val)
                setattr(phase, key, val)

            session.commit()
            return True

    def remove_phase(self, phase_id: int) -> bool:
        """Remove a phase from a plan."""
        with self._get_session() as session:
            phase = session.query(TrainingPhase).filter(TrainingPhase.phase_id == phase_id).first()
            if phase is None:
                return False
            session.delete(phase)
            session.commit()
            return True

    def deactivate_plan(self, plan_id: Optional[int] = None) -> bool:
        """Deactivate a plan (or the active plan if no ID given)."""
        with self._get_session() as session:
            if plan_id:
                plan = session.query(TrainingPlan).filter(TrainingPlan.plan_id == plan_id).first()
            else:
                plan = session.query(TrainingPlan).filter(TrainingPlan.is_active == True).first()
            if plan is None:
                return False
            plan.is_active = False
            session.commit()
            return True

    # ------ Training Week Methods ------

    def add_week(
        self,
        plan_id: int,
        week_number: int,
        start_date: str,
        end_date: str,
        phase_id: Optional[int] = None,
        target_km: Optional[float] = None,
        target_vert_m: Optional[float] = None,
        target_long_run_km: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> int:
        """Add a week row to a training plan. Returns week_id."""
        from datetime import date as date_type
        with self._get_session() as session:
            week = TrainingWeek(
                plan_id=plan_id,
                phase_id=phase_id,
                week_number=week_number,
                start_date=date_type.fromisoformat(start_date),
                end_date=date_type.fromisoformat(end_date),
                target_km=target_km,
                target_vert_m=target_vert_m,
                target_long_run_km=target_long_run_km,
                notes=notes,
            )
            session.add(week)
            session.commit()
            session.refresh(week)
            return week.week_id

    def get_plan_weeks(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get all weeks for a plan, ordered by week_number."""
        with self._get_session() as session:
            weeks = (
                session.query(TrainingWeek)
                .filter(TrainingWeek.plan_id == plan_id)
                .order_by(TrainingWeek.week_number.asc())
                .all()
            )
            return [
                {
                    "week_id": w.week_id,
                    "phase_id": w.phase_id,
                    "week_number": w.week_number,
                    "start_date": w.start_date.isoformat(),
                    "end_date": w.end_date.isoformat(),
                    "target_km": w.target_km,
                    "target_vert_m": w.target_vert_m,
                    "target_long_run_km": w.target_long_run_km,
                    "notes": w.notes,
                }
                for w in weeks
            ]

    def update_week(self, week_id: int, **kwargs) -> bool:
        """Update fields on an existing week."""
        from datetime import date as date_type
        with self._get_session() as session:
            week = session.query(TrainingWeek).filter(TrainingWeek.week_id == week_id).first()
            if week is None:
                return False
            for key, val in kwargs.items():
                if val is None:
                    continue
                if key in ("start_date", "end_date") and isinstance(val, str):
                    val = date_type.fromisoformat(val)
                setattr(week, key, val)
            session.commit()
            return True

    def remove_week(self, week_id: int) -> bool:
        """Remove a single week row."""
        with self._get_session() as session:
            week = session.query(TrainingWeek).filter(TrainingWeek.week_id == week_id).first()
            if week is None:
                return False
            session.delete(week)
            session.commit()
            return True

    def remove_plan_weeks(self, plan_id: int) -> int:
        """Remove all weeks for a plan. Returns count removed."""
        with self._get_session() as session:
            count = session.query(TrainingWeek).filter(TrainingWeek.plan_id == plan_id).delete()
            session.commit()
            return count

    # ------ Utility Methods ------
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of all stored context for agent prompting."""
        profile = self.get_profile()
        goals = self.get_active_goals()
        current_episodes = self.current_episodes()
        recent_conversations = self.last_n_turns(10)
        
        return {
            "profile": profile,
            "active_goals": goals,
            "current_episodes": current_episodes,
            "recent_conversations": recent_conversations
        }
