#!/usr/bin/env python3
"""
LangChain Agent for Ultra Trainer

This module initializes a LangChain agent that connects OpenAI's GPT-4o model
with Strava MCP tools for ultra marathon training assistance.
"""

import os
from typing import Any, Dict, List, Type

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ultra_trainer.strava_mcp_server import server

# Load environment variables
load_dotenv()


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
    system_message = """You are an expert ultra marathon training assistant with access to Strava activity data.

Your role is to help athletes:
- Analyze their training patterns and performance
- Provide personalized training advice for ultra marathons
- Track progress and identify areas for improvement
- Suggest training plans based on current fitness and goals
- Help with race preparation and recovery strategies

You have access to the following Strava data through tools:
- Recent activities and training history
- Detailed activity metrics (distance, time, elevation, etc.)
- Activities within specific date ranges
- Individual activity details

When analyzing data:
- Focus on relevant metrics for ultra marathon training (weekly mileage, long runs, elevation gain, etc.)
- Consider training consistency and progression
- Look for patterns in performance and recovery
- Provide actionable insights and recommendations

When displaying activity information:
- ALWAYS prominently show the activity name (e.g., "Morning Run", "Long Trail Run", etc.) as the main title or header
- Include the activity name in quotes when referring to specific activities
- Use the activity name to provide context about the type of workout
- Present the activity name before other details like distance, time, etc.

Always be encouraging and supportive while providing evidence-based advice.
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
    tools = get_strava_tools()
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
        max_iterations=10,
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
