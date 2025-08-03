#!/usr/bin/env python3
"""
Context Store for Ultra Trainer

This module provides a persistent SQLite datastore for athlete profile,
goals, episodes (injury/fatigue logs), and conversation history.
"""

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Enum, Float
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
    fitness_level = Column(Integer)  # 1-10 scale
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
        ultra_experience: Optional[int] = None
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
        fitness_level: Optional[int] = None
    ) -> int:
        """Add new goal or update existing goal. Returns goal_id."""
        with self._get_session() as session:
            if goal_id:
                # Update existing goal
                goal = session.query(Goal).filter(Goal.goal_id == goal_id).first()
                if goal is None:
                    raise ValueError(f"Goal with ID {goal_id} not found")
            else:
                # Create new goal
                goal = Goal()
                session.add(goal)
            
            # Update fields if provided
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
            if fitness_level is not None:
                goal.fitness_level = fitness_level
            
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
                    "fitness_level": goal.fitness_level,
                    "created_at": goal.created_at.isoformat() if goal.created_at else None,
                    "updated_at": goal.updated_at.isoformat() if goal.updated_at else None
                }
                for goal in goals
            ]
    
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


# Import fix for datetime
from datetime import timedelta
