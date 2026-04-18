#!/usr/bin/env python3
"""
LangChain Agent for Ultra Trainer

This module initializes a LangChain agent that connects OpenAI's GPT-4o model
with Strava MCP tools and persistent data store for ultra marathon training assistance.
"""

import os
import json
import tempfile
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Type, Optional

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import BaseTool, tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ultra_trainer.strava_mcp_server import server
from ultra_trainer.context_store import ContextStore
from ultra_trainer.prompts import create_agent_prompt

# Load environment variables
load_dotenv()


def get_store() -> ContextStore:
    """Get a context store instance."""
    return ContextStore()


class StravaToolInput(BaseModel):
    """Input schema for Strava tools."""
    limit: int = Field(default=10, description="Maximum number of activities to return")


class StravaDateRangeToolInput(BaseModel):
    """Input schema for Strava date range tools."""
    start_date: str = Field(description="Start date in ISO format (YYYY-MM-DD)")
    end_date: str = Field(description="End date in ISO format (YYYY-MM-DD)")
    limit: int = Field(default=30, description="Maximum number of activities to return")


class StravaActivityToolInput(BaseModel):
    """Input schema for Strava activity tools."""
    activity_id: int = Field(description="ID of the activity to retrieve")


class StravaRecentToolInput(BaseModel):
    """Input schema for Strava recent activities tools."""
    days: int = Field(default=7, description="Number of days to look back")
    limit: int = Field(default=10, description="Maximum number of activities to return")


class StravaGetActivitiesTool(BaseTool):
    """LangChain tool wrapper for Strava get_activities MCP function."""
    
    name: str = "get_strava_activities"
    description: str = "Get the authenticated athlete's recent activities from Strava"
    args_schema: Type[BaseModel] = StravaToolInput
    
    def _run(self, limit: int = 10) -> Dict[str, Any]:
        """Execute the tool."""
        try:
            return server.get_activities(limit=limit)
        except Exception as e:
            return {"error": f"Failed to get activities: {str(e)}"}


class StravaGetActivitiesByDateRangeTool(BaseTool):
    """LangChain tool wrapper for Strava get_activities_by_date_range MCP function."""
    
    name: str = "get_strava_activities_by_date_range"
    description: str = "Get activities within a specific date range from Strava"
    args_schema: Type[BaseModel] = StravaDateRangeToolInput
    
    def _run(self, start_date: str, end_date: str, limit: int = 30) -> Dict[str, Any]:
        """Execute the tool."""
        try:
            return server.get_activities_by_date_range(
                start_date=start_date, 
                end_date=end_date, 
                limit=limit
            )
        except Exception as e:
            return {"error": f"Failed to get activities by date range: {str(e)}"}


class StravaGetActivityByIdTool(BaseTool):
    """LangChain tool wrapper for Strava get_activity_by_id MCP function."""
    
    name: str = "get_strava_activity_by_id"
    description: str = "Get detailed information about a specific activity from Strava"
    args_schema: Type[BaseModel] = StravaActivityToolInput
    
    def _run(self, activity_id: int) -> Dict[str, Any]:
        """Execute the tool."""
        try:
            return server.get_activity_by_id(activity_id=activity_id)
        except Exception as e:
            return {"error": f"Failed to get activity by ID: {str(e)}"}


class StravaGetRecentActivitiesTool(BaseTool):
    """LangChain tool wrapper for Strava get_recent_activities MCP function."""
    
    name: str = "get_strava_recent_activities"
    description: str = "Get activities from the past X days from Strava (rolling window from now, NOT aligned to calendar weeks). For weekly volume, use weekly_volume instead."
    args_schema: Type[BaseModel] = StravaRecentToolInput
    
    def _run(self, days: int = 7, limit: int = 10) -> Dict[str, Any]:
        """Execute the tool."""
        try:
            return server.get_recent_activities(days=days, limit=limit)
        except Exception as e:
            return {"error": f"Failed to get recent activities: {str(e)}"}


def get_strava_tools() -> List[BaseTool]:
    """Get all Strava MCP tools wrapped as LangChain tools."""
    return [
        StravaGetActivitiesTool(),
        StravaGetActivitiesByDateRangeTool(),
        StravaGetActivityByIdTool(),
        StravaGetRecentActivitiesTool(),
    ]


# ------ Data Store Tools ------

@tool("profile")
def profile_tool(
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
) -> str:
    """
    Update or query the athlete profile.
    If no args are supplied, returns the current profile.
    Use this to remember athlete details across conversations.
    Location fields can include city, state/province, country (e.g., "Boulder, Colorado, USA").
    """
    store = get_store()
    
    # If any parameters provided, update profile
    if any([birth_year, gender, history, weight_kg, running_years, 
            preferred_terrain, weekly_mileage_km, ultra_experience,
            current_location, default_location]):
        store.upsert_profile(
            birth_year=birth_year,
            gender=gender,
            history=history,
            weight_kg=weight_kg,
            running_years=running_years,
            preferred_terrain=preferred_terrain,
            weekly_mileage_km=weekly_mileage_km,
            ultra_experience=ultra_experience,
            current_location=current_location,
            default_location=default_location
        )
        return "✅ Profile updated successfully."
    
    # Otherwise return current profile
    prof = store.get_profile()
    if prof is None:
        return "No profile found. You can create one by providing details like birth_year, weight_kg, etc."
    
    return f"Current profile: {json.dumps(prof, default=str, indent=2)}"


@tool("goals")
def goals_tool(
    event_name: Optional[str] = None,
    distance_km: Optional[float] = None,
    event_date: Optional[str] = None,
    context_text: Optional[str] = None,
    target_time_seconds: Optional[int] = None,
    race_priority: Optional[str] = None,
    remove_goal: Optional[str] = None,
    remove_goal_id: Optional[int] = None,
    update_goal_id: Optional[int] = None,
) -> str:
    """
    Add a new goal, update an existing goal, remove a goal, or view current goals.
    If no args supplied, returns current active goals.
    Use event_date in ISO format like '2025-10-15' for October 15, 2025.
    race_priority: "A" (primary target), "B" (intermediary), or "C" (training race).
    To update an existing goal, provide update_goal_id along with fields to change.
    To remove a goal, use remove_goal (event name) or remove_goal_id (goal ID).
    """
    store = get_store()

    if remove_goal or remove_goal_id:
        success = store.remove_goal(goal_id=remove_goal_id, event_name=remove_goal)
        target = remove_goal or f"goal ID {remove_goal_id}"
        return f"✅ Goal '{target}' removed." if success else f"❌ Could not find goal '{target}'."

    if update_goal_id:
        event_datetime = None
        if event_date:
            try:
                event_datetime = datetime.fromisoformat(event_date).replace(tzinfo=timezone.utc)
            except ValueError:
                return f"❌ Invalid date format: {event_date}"
        goal_id = store.add_or_update_goal(
            goal_id=update_goal_id,
            event_name=event_name,
            distance_km=distance_km,
            event_datetime=event_datetime,
            context_text=context_text,
            target_time_seconds=target_time_seconds,
            race_priority=race_priority,
        )
        return f"✅ Goal ID {goal_id} updated."

    if event_name:
        event_datetime = None
        if event_date:
            try:
                event_datetime = datetime.fromisoformat(event_date).replace(tzinfo=timezone.utc)
            except ValueError:
                return f"❌ Invalid date format: {event_date}"
        goal_id = store.add_or_update_goal(
            event_name=event_name,
            distance_km=distance_km,
            event_datetime=event_datetime,
            context_text=context_text,
            target_time_seconds=target_time_seconds,
            race_priority=race_priority,
        )
        return f"✅ Goal '{event_name}' added (ID: {goal_id})."

    goals = store.get_active_goals()
    if not goals:
        return "No active goals found."
    return f"Active goals: {json.dumps(goals, default=str, indent=2)}"


@tool("injury")
def injury_tool(
    status: Optional[str] = None,
    description: Optional[str] = None,
    severity: Optional[int] = None,
    end_injury: Optional[int] = None
) -> str:
    """
    Log injury status or view current injuries.
    - status: 'new' to log new injury, 'current' to view ongoing injuries
    - description: details about the injury
    - severity: 1-10 scale (10 = severe)
    - end_injury: episode_id to mark an injury as resolved
    """
    store = get_store()
    
    if end_injury:
        success = store.end_episode(end_injury)
        return f"✅ Injury episode {end_injury} marked as resolved." if success else f"❌ Could not find injury episode {end_injury}."
    
    if status == "new" and description:
        episode_id = store.log_episode(
            topic="injury",
            narrative=description,
            severity=severity
        )
        return f"✅ Injury logged successfully (Episode ID: {episode_id})."
    
    # Return current injuries
    injuries = store.current_episodes(topic="injury")
    if not injuries:
        return "No current injuries recorded. Good news! 🎉"
    
    return f"Current injuries: {json.dumps(injuries, default=str, indent=2)}"


@tool("fatigue")
def fatigue_tool(
    status: Optional[str] = None,
    description: Optional[str] = None,
    severity: Optional[int] = None,
    end_fatigue: Optional[int] = None
) -> str:
    """
    Log fatigue status or view current fatigue episodes.
    - status: 'new' to log fatigue, 'current' to view ongoing fatigue
    - description: details about fatigue level, sleep, stress, etc.
    - severity: 1-10 scale (10 = extremely fatigued)
    - end_fatigue: episode_id to mark fatigue as resolved
    """
    store = get_store()
    
    if end_fatigue:
        success = store.end_episode(end_fatigue)
        return f"✅ Fatigue episode {end_fatigue} marked as resolved." if success else f"❌ Could not find fatigue episode {end_fatigue}."
    
    if status == "new" and description:
        episode_id = store.log_episode(
            topic="fatigue",
            narrative=description,
            severity=severity
        )
        return f"✅ Fatigue logged successfully (Episode ID: {episode_id})."
    
    # Return current fatigue episodes
    fatigue_episodes = store.current_episodes(topic="fatigue")
    if not fatigue_episodes:
        return "No current fatigue episodes recorded."
    
    return f"Current fatigue: {json.dumps(fatigue_episodes, default=str, indent=2)}"


@tool("effort")
def effort_tool(
    description: Optional[str] = None,
    severity: Optional[int] = None
) -> str:
    """
    Log perceived effort for recent training.
    - description: details about effort level, how training felt
    - severity: 1-10 scale (10 = maximum effort)
    """
    store = get_store()
    
    if description:
        episode_id = store.log_episode(
            topic="effort",
            narrative=description,
            severity=severity
        )
        return f"✅ Effort logged successfully (Episode ID: {episode_id})."
    
    # Return recent effort logs
    recent_efforts = store.get_recent_episodes(days=7, topic="effort")
    if not recent_efforts:
        return "No recent effort logs found."
    
    return f"Recent effort logs: {json.dumps(recent_efforts, default=str, indent=2)}"


@tool("episode_history")
def episode_history_tool(
    topic: Optional[str] = None,
    days: int = 30
) -> str:
    """
    Get recent episode history (injuries, fatigue, effort, etc.).
    - topic: filter by specific topic ('injury', 'fatigue', 'effort', etc.) or None for all
    - days: number of days to look back (default 30)
    """
    store = get_store()
    
    episodes = store.get_recent_episodes(days=days, topic=topic)
    if not episodes:
        filter_text = f" for topic '{topic}'" if topic else ""
        return f"No episodes found in the last {days} days{filter_text}."
    
    return f"Recent episodes (last {days} days): {json.dumps(episodes, default=str, indent=2)}"


@tool("conversation_context")
def conversation_context_tool() -> str:
    """
    Get stored conversation context and athlete summary.
    Use this to remember what you've discussed with the athlete previously.
    Includes compacted summaries of past coaching sessions.
    """
    store = get_store()
    context = store.get_context_summary()
    conversation_history = store.get_conversation_history(max_entries=10)
    active_plan = store.get_active_plan()

    parts = [f"Stored context: {json.dumps(context, default=str, indent=2)}"]
    if active_plan:
        parts.append(f"\nActive training plan: {json.dumps(active_plan, default=str, indent=2)}")
    if conversation_history:
        parts.append(f"\n{conversation_history}")
    return "\n".join(parts)


@tool("weekly_volume")
def weekly_volume_tool(week_offset: int = 0) -> str:
    """
    Get training activities for a specific calendar week (Monday-Sunday).
    week_offset: 0 = current week, -1 = last week, -2 = two weeks ago, etc.
    Returns all activities within that Monday-Sunday period.
    """
    today = datetime.now(timezone.utc).date()
    current_monday = today - timedelta(days=today.weekday())
    target_monday = current_monday + timedelta(weeks=week_offset)
    target_sunday = target_monday + timedelta(days=6)

    try:
        result = server.get_activities_by_date_range(
            start_date=target_monday.isoformat(),
            end_date=target_sunday.isoformat(),
            limit=50,
        )
        return f"Week {target_monday} to {target_sunday}:\n{json.dumps(result, default=str, indent=2)}"
    except Exception as e:
        return f"Failed to get weekly volume: {str(e)}"


@tool("training_plan")
def training_plan_tool(
    action: str = "view",
    plan_name: Optional[str] = None,
    a_race_goal_id: Optional[int] = None,
    phase_type: Optional[str] = None,
    phase_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    target_weekly_km: Optional[float] = None,
    target_weekly_vert_m: Optional[float] = None,
    target_long_run_km: Optional[float] = None,
    notes: Optional[str] = None,
    order_index: Optional[int] = None,
    phase_id: Optional[int] = None,
    plan_id: Optional[int] = None,
    week_number: Optional[int] = None,
    week_id: Optional[int] = None,
    target_km: Optional[float] = None,
    target_vert_m: Optional[float] = None,
    target_week_long_run_km: Optional[float] = None,
    weeks_json: Optional[str] = None,
) -> str:
    """
    Manage the Koop-style training plan. Actions:
    - "view": Show the active plan with all phases and weekly volume table.
    - "create": Create a new plan. Requires plan_name and a_race_goal_id.
    - "add_phase": Add a phase. Requires phase_type (base/specific/race_specific/taper/recovery),
      start_date, end_date (YYYY-MM-DD). Optional: phase_name, target_weekly_km,
      target_weekly_vert_m, target_long_run_km, notes, order_index.
    - "update_phase": Update a phase. Requires phase_id plus fields to change.
    - "remove_phase": Remove a phase. Requires phase_id.
    - "add_week": Add a week row. Requires week_number, start_date, end_date (YYYY-MM-DD).
      Optional: phase_id, target_km, target_vert_m, target_week_long_run_km, notes.
    - "update_week": Update a week. Requires week_id plus fields to change.
    - "remove_week": Remove a week. Requires week_id.
    - "set_weeks": Bulk-set the weekly table. Provide weeks_json as a JSON array of objects
      with keys: week_number, start_date, end_date, phase_id, target_km, target_vert_m,
      target_long_run_km, notes. Replaces all existing weeks for the plan.
    - "deactivate": Deactivate the current plan (or specify plan_id).
    """
    store = get_store()

    if action == "create":
        if not plan_name or not a_race_goal_id:
            return "❌ plan_name and a_race_goal_id are required to create a plan."
        pid = store.create_plan(name=plan_name, a_race_goal_id=a_race_goal_id)
        return f"✅ Training plan '{plan_name}' created (ID: {pid})."

    if action == "add_phase":
        plan = store.get_active_plan()
        if plan is None:
            return "❌ No active training plan. Create one first."
        if not phase_type or not start_date or not end_date:
            return "❌ phase_type, start_date, and end_date are required."
        pid = store.add_phase(
            plan_id=plan["plan_id"],
            phase_type=phase_type,
            start_date=start_date,
            end_date=end_date,
            name=phase_name,
            target_weekly_km=target_weekly_km,
            target_weekly_vert_m=target_weekly_vert_m,
            target_long_run_km=target_long_run_km,
            notes=notes,
            order_index=order_index,
        )
        return f"✅ Phase '{phase_name or phase_type}' added (ID: {pid})."

    if action == "update_phase":
        if not phase_id:
            return "❌ phase_id is required."
        kwargs = {}
        if phase_type is not None: kwargs["phase_type"] = phase_type
        if phase_name is not None: kwargs["name"] = phase_name
        if start_date is not None: kwargs["start_date"] = start_date
        if end_date is not None: kwargs["end_date"] = end_date
        if target_weekly_km is not None: kwargs["target_weekly_km"] = target_weekly_km
        if target_weekly_vert_m is not None: kwargs["target_weekly_vert_m"] = target_weekly_vert_m
        if target_long_run_km is not None: kwargs["target_long_run_km"] = target_long_run_km
        if notes is not None: kwargs["notes"] = notes
        if order_index is not None: kwargs["order_index"] = order_index
        success = store.update_phase(phase_id, **kwargs)
        return f"✅ Phase {phase_id} updated." if success else f"❌ Phase {phase_id} not found."

    if action == "remove_phase":
        if not phase_id:
            return "❌ phase_id is required."
        success = store.remove_phase(phase_id)
        return f"✅ Phase {phase_id} removed." if success else f"❌ Phase {phase_id} not found."

    if action == "add_week":
        plan = store.get_active_plan()
        if plan is None:
            return "❌ No active training plan. Create one first."
        if not week_number or not start_date or not end_date:
            return "❌ week_number, start_date, and end_date are required."
        wid = store.add_week(
            plan_id=plan["plan_id"],
            week_number=week_number,
            start_date=start_date,
            end_date=end_date,
            phase_id=phase_id,
            target_km=target_km,
            target_vert_m=target_vert_m,
            target_long_run_km=target_week_long_run_km,
            notes=notes,
        )
        return f"✅ Week {week_number} added (ID: {wid})."

    if action == "update_week":
        if not week_id:
            return "❌ week_id is required."
        kwargs = {}
        if week_number is not None: kwargs["week_number"] = week_number
        if start_date is not None: kwargs["start_date"] = start_date
        if end_date is not None: kwargs["end_date"] = end_date
        if phase_id is not None: kwargs["phase_id"] = phase_id
        if target_km is not None: kwargs["target_km"] = target_km
        if target_vert_m is not None: kwargs["target_vert_m"] = target_vert_m
        if target_week_long_run_km is not None: kwargs["target_long_run_km"] = target_week_long_run_km
        if notes is not None: kwargs["notes"] = notes
        success = store.update_week(week_id, **kwargs)
        return f"✅ Week {week_id} updated." if success else f"❌ Week {week_id} not found."

    if action == "remove_week":
        if not week_id:
            return "❌ week_id is required."
        success = store.remove_week(week_id)
        return f"✅ Week {week_id} removed." if success else f"❌ Week {week_id} not found."

    if action == "set_weeks":
        plan = store.get_active_plan()
        if plan is None:
            return "❌ No active training plan. Create one first."
        if not weeks_json:
            return "❌ weeks_json is required (JSON array of week objects)."
        try:
            weeks_data = json.loads(weeks_json)
        except json.JSONDecodeError as e:
            return f"❌ Invalid JSON: {e}"
        removed = store.remove_plan_weeks(plan["plan_id"])
        added = 0
        for w in weeks_data:
            store.add_week(
                plan_id=plan["plan_id"],
                week_number=w["week_number"],
                start_date=w["start_date"],
                end_date=w["end_date"],
                phase_id=w.get("phase_id"),
                target_km=w.get("target_km"),
                target_vert_m=w.get("target_vert_m"),
                target_long_run_km=w.get("target_long_run_km"),
                notes=w.get("notes"),
            )
            added += 1
        return f"✅ Weekly table set: {removed} old weeks removed, {added} weeks added."

    if action == "deactivate":
        success = store.deactivate_plan(plan_id)
        return "✅ Plan deactivated." if success else "❌ No active plan to deactivate."

    # Default: view
    plan = store.get_active_plan()
    if plan is None:
        return "No active training plan. Use action='create' to create one."
    return f"Active training plan: {json.dumps(plan, default=str, indent=2)}"


@tool("chart")
def chart_tool(
    chart_type: str,
    data_json: str,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
) -> str:
    """
    Generate a chart image and return a marker for Streamlit rendering.

    chart_type options:
    - "weekly_volume": bar chart of weekly distance (km). data_json keys: week, km, race (optional bool)
    - "weekly_elevation": bar chart of weekly elevation (m). data_json keys: week, vert_m, race (optional bool)
    - "weekly_combined": dual-axis chart — bars for km (left), line for elevation (right).
      data_json keys: week, km, vert_m, race (optional bool — marks race/event weeks in a different color)
    - "bar": generic bar chart. data_json keys: label, value
    - "line": generic line chart. data_json keys: label, value

    data_json: JSON array of objects, e.g. [{"week":"W14","km":80,"vert_m":2000}, ...]
    title: chart title (optional)
    x_label / y_label: axis labels (optional)

    Returns a [CHART:<path>] marker that the UI renders as an image.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        data = json.loads(data_json)
    except json.JSONDecodeError as e:
        return f"❌ Invalid data_json: {e}"

    fig, ax = plt.subplots(figsize=(10, 4))

    if chart_type == "weekly_volume":
        weeks = [d.get("week", "") for d in data]
        kms = [d.get("km", 0) for d in data]
        colors = ["#E91E63" if d.get("race") else "#2196F3" for d in data]
        ax.bar(weeks, kms, color=colors)
        ax.set_ylabel(y_label or "Distance (km)")
        ax.set_title(title or "Weekly Volume")

    elif chart_type == "weekly_elevation":
        weeks = [d.get("week", "") for d in data]
        verts = [d.get("vert_m", 0) for d in data]
        colors = ["#E91E63" if d.get("race") else "#4CAF50" for d in data]
        ax.bar(weeks, verts, color=colors)
        ax.set_ylabel(y_label or "Elevation (m)")
        ax.set_title(title or "Weekly Elevation")

    elif chart_type == "weekly_combined":
        weeks = [d.get("week", "") for d in data]
        kms = [d.get("km", 0) for d in data]
        verts = [d.get("vert_m", 0) for d in data]
        colors = ["#E91E63" if d.get("race") else "#2196F3" for d in data]
        bars = ax.bar(weeks, kms, color=colors, alpha=0.7, label="Distance (km)")
        ax.set_ylabel(y_label or "Distance (km)")
        ax2 = ax.twinx()
        ax2.plot(weeks, verts, color="#FF5722", marker="o", linewidth=2, label="Elevation (m)")
        ax2.set_ylabel("Elevation (m)")
        # Build legend with race color entry if any race weeks exist
        from matplotlib.patches import Patch
        handles = [Patch(facecolor="#2196F3", alpha=0.7, label="Distance (km)")]
        if any(d.get("race") for d in data):
            handles.append(Patch(facecolor="#E91E63", alpha=0.7, label="Race week"))
        ax.legend(handles=handles, loc="upper left")
        ax2.legend(loc="upper right")
        ax.set_title(title or "Weekly Volume & Elevation")

    elif chart_type == "bar":
        labels = [d.get("label", "") for d in data]
        values = [d.get("value", 0) for d in data]
        ax.bar(labels, values, color="#2196F3")
        if y_label:
            ax.set_ylabel(y_label)
        ax.set_title(title or "Chart")

    elif chart_type == "line":
        labels = [d.get("label", "") for d in data]
        values = [d.get("value", 0) for d in data]
        ax.plot(labels, values, color="#2196F3", marker="o", linewidth=2)
        if y_label:
            ax.set_ylabel(y_label)
        ax.set_title(title or "Chart")

    else:
        plt.close(fig)
        return f"❌ Unknown chart_type: {chart_type}"

    if x_label:
        ax.set_xlabel(x_label)

    # Draw a vertical line on the current week if present
    from datetime import date as date_type
    today = date_type.today()
    current_week_label = f"W{today.isocalendar()[1]:02d}"
    current_monday = today - timedelta(days=today.weekday())
    current_monday_str = current_monday.isoformat()

    tick_labels = [d.get("week", d.get("label", "")) for d in data]
    current_idx = None
    # Match by "W13" style label
    if current_week_label in tick_labels:
        current_idx = tick_labels.index(current_week_label)
    else:
        # Match by date: find the label whose start_date falls in the current week
        for i, d in enumerate(data):
            start = d.get("start_date", "")
            label = tick_labels[i]
            if start == current_monday_str or label == current_monday_str:
                current_idx = i
                break
            # Also try parsing the label as a date to see if it's in current week
            try:
                label_date = date_type.fromisoformat(label)
                if current_monday <= label_date <= current_monday + timedelta(days=6):
                    current_idx = i
                    break
            except (ValueError, TypeError):
                pass
    if current_idx is not None:
        ax.axvline(x=current_idx, color="gray", linestyle="--", linewidth=1.5, alpha=0.7)
        ax.text(current_idx, ax.get_ylim()[1] * 0.95, "now", ha="center", va="top",
                fontsize=8, color="gray", fontstyle="italic")

    for label in ax.get_xticklabels():
        label.set_rotation(90)
        label.set_ha("center")
        label.set_fontsize(8)
    plt.tight_layout()

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    fig.savefig(tmp.name, dpi=150)
    plt.close(fig)

    return f"[CHART:{tmp.name}]"


def get_datastore_tools() -> List:
    """Get all data store tools."""
    return [
        profile_tool,
        goals_tool,
        injury_tool,
        fatigue_tool,
        effort_tool,
        episode_history_tool,
        conversation_context_tool,
        weekly_volume_tool,
        training_plan_tool,
        chart_tool,
    ]


def get_all_tools() -> List:
    """Get all tools (Strava + Data Store)."""
    return get_strava_tools() + get_datastore_tools()


def initialize_llm() -> ChatOpenAI:
    """Initialize the OpenAI LLM client."""
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    # o3 models don't support custom temperature settings
    llm_kwargs = {
        "api_key": api_key,
        "model": model,
    }
    
    # Only add temperature for models that support it
    if model.startswith("gpt-5"):
        llm_kwargs["temperature"] = 1
    elif not model.startswith("o3"):
        llm_kwargs["temperature"] = 0.1  # Low temperature for more consistent responses
    
    return ChatOpenAI(**llm_kwargs)


def create_ultra_trainer_agent() -> AgentExecutor:
    """Create and return the configured ultra trainer agent."""
    # Initialize components
    llm = initialize_llm()
    tools = get_all_tools()  # Use all tools (Strava + Data Store)
    
    # Get current location from athlete profile for context
    store = get_store()
    profile = store.get_profile()
    current_location = None
    if profile:
        current_location = profile.get('current_location') or profile.get('default_location')
    
    # Create agent prompt with location context
    prompt = create_agent_prompt(current_location=current_location)  
    
    # Ensure Strava client is initialized
    if server.strava_client is None:
        refresh_token = os.getenv("STRAVA_REFRESH_TOKEN")
        client_id = os.getenv("STRAVA_CLIENT_ID")
        client_secret = os.getenv("STRAVA_CLIENT_SECRET")
        
        if not all([refresh_token, client_id, client_secret]):
            raise ValueError(
                "Strava credentials not configured. Please set STRAVA_REFRESH_TOKEN, "
                "STRAVA_CLIENT_ID, and STRAVA_CLIENT_SECRET environment variables."
            )
        
        server.strava_client = server.StravaClient(
            refresh_token, client_id, client_secret
        )
    
    # Create the agent
    agent = create_openai_tools_agent(llm, tools, prompt)
    
    # Create and return the agent executor
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=15,  # Increased for more complex multi-tool workflows
    )


def get_agent() -> AgentExecutor:
    """Get a configured ultra trainer agent instance."""
    return create_ultra_trainer_agent()


if __name__ == "__main__":
    # Example usage
    agent = get_agent()
    
    # Test the agent
    response = agent.invoke({
        "input": "Show me my recent running activities and provide a brief analysis of my training."
    })
    
    print("Agent Response:")
    print(response["output"])
