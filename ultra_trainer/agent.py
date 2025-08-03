#!/usr/bin/env python3
"""
LangChain Agent for Ultra Trainer

This module initializes a LangChain agent that connects OpenAI's GPT-4o model
with Strava MCP tools and persistent data store for ultra marathon training assistance.
"""

import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Type, Optional

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import BaseTool, tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ultra_trainer.strava_mcp_server import server
from ultra_trainer.context_store import ContextStore

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
    description: str = "Get activities from the past X days from Strava"
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
    ultra_experience: Optional[int] = None
) -> str:
    """
    Update or query the athlete profile.
    If no args are supplied, returns the current profile.
    Use this to remember athlete details across conversations.
    """
    store = get_store()
    
    # If any parameters provided, update profile
    if any([birth_year, gender, history, weight_kg, running_years, 
            preferred_terrain, weekly_mileage_km, ultra_experience]):
        store.upsert_profile(
            birth_year=birth_year,
            gender=gender,
            history=history,
            weight_kg=weight_kg,
            running_years=running_years,
            preferred_terrain=preferred_terrain,
            weekly_mileage_km=weekly_mileage_km,
            ultra_experience=ultra_experience
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
    remove_goal: Optional[str] = None,
    remove_goal_id: Optional[int] = None
) -> str:
    """
    Add a new goal, remove an existing goal, or view current goals.
    If no args supplied, returns current active goals.
    Use event_date in ISO format like '2025-10-15' for October 15, 2025.
    To remove a goal, use remove_goal (event name) or remove_goal_id (goal ID).
    """
    store = get_store()
    
    # Handle goal removal
    if remove_goal or remove_goal_id:
        success = store.remove_goal(goal_id=remove_goal_id, event_name=remove_goal)
        if success:
            target = remove_goal or f"goal ID {remove_goal_id}"
            return f"✅ Goal '{target}' removed successfully."
        else:
            target = remove_goal or f"goal ID {remove_goal_id}"
            return f"❌ Could not find goal '{target}' to remove."
    
    # If parameters provided, add new goal
    if event_name:
        event_datetime = None
        if event_date:
            try:
                # Parse ISO date string to datetime
                event_datetime = datetime.fromisoformat(event_date).replace(tzinfo=timezone.utc)
            except ValueError:
                return f"❌ Invalid date format. Use YYYY-MM-DD format, got: {event_date}"
        
        goal_id = store.add_or_update_goal(
            event_name=event_name,
            distance_km=distance_km,
            event_datetime=event_datetime,
            context_text=context_text,
            target_time_seconds=target_time_seconds
        )
        return f"✅ Goal '{event_name}' added successfully (ID: {goal_id})."
    
    # Otherwise return current goals
    goals = store.get_active_goals()
    if not goals:
        return "No active goals found. Add a goal by providing event_name and other details."
    
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
    """
    store = get_store()
    context = store.get_context_summary()
    return f"Stored context: {json.dumps(context, default=str, indent=2)}"


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
    
    return ChatOpenAI(
        api_key=api_key,
        model=model,
        temperature=0.1,  # Low temperature for more consistent responses
    )


def create_agent_prompt() -> ChatPromptTemplate:
    """Create the prompt template for the ultra training agent."""
    system_message = """You are an expert ultra marathon training assistant with access to Strava activity data and persistent memory storage.

Your role is to help athletes:
- Analyze their training patterns and performance
- Provide personalized training advice for ultra marathons
- Track progress and identify areas for improvement
- Suggest training plans based on current fitness and goals
- Help with race preparation and recovery strategies
- Remember athlete context across conversations

You have access to the following data sources:

STRAVA DATA (via tools):
- Recent activities and training history
- Detailed activity metrics (distance, time, elevation, etc.)
- Activities within specific date ranges
- Individual activity details

PERSISTENT MEMORY (via tools):
- Athlete profile (age, weight, experience, terrain preferences, etc.)
- Training goals and target races
- Injury and fatigue episodes
- Effort and training feedback logs
- Conversation history and context

IMPORTANT MEMORY USAGE:
- ALWAYS check conversation_context_tool at the start of conversations to understand what you know about the athlete
- Use profile_tool to remember/update athlete details (age, experience, goals, etc.)
- Use goals_tool to track target races and training objectives
- Use injury_tool and fatigue_tool to monitor athlete health and recovery
- Use effort_tool to track how training feels to the athlete
- Store relevant information from conversations for future reference

When analyzing data:
- Focus on relevant metrics for ultra marathon training (weekly mileage, long runs, elevation gain, etc.)
- Consider training consistency and progression
- Look for patterns in performance and recovery
- Provide actionable insights and recommendations
- Remember athlete preferences and past conversations

When displaying activity information:
- ALWAYS prominently show the activity name (e.g., "Morning Run", "Long Trail Run", etc.) as the main title or header
- Include the activity name in quotes when referring to specific activities
- Use the activity name to provide context about the type of workout
- Present the activity name before other details like distance, time, etc.

Always be encouraging and supportive while providing evidence-based advice. Remember that continuity and personalization are key to effective coaching.
"""
    
    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])


def create_ultra_trainer_agent() -> AgentExecutor:
    """Create and return the configured ultra trainer agent."""
    # Initialize components
    llm = initialize_llm()
    tools = get_all_tools()  # Use all tools (Strava + Data Store)
    prompt = create_agent_prompt()
    
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
