#!/usr/bin/env python3
"""
Streamlit Web Interface for Ultra Trainer

This module provides a web-based chat interface for the ultra marathon training agent.
It provides a simple multi-turn conversation interface without persistent storage
or special commands for now.
"""

import os
import re
import uuid
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv

from ultra_trainer.agent import get_agent, initialize_llm
from ultra_trainer.context_store import ContextStore

# Load environment variables
load_dotenv()

_CHART_RE = re.compile(r"\[CHART:([^\]]+)\]")


def render_message(content: str):
    """Render a message, replacing [CHART:<path>] markers with images."""
    parts = _CHART_RE.split(content)
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part.strip():
                st.write(part)
        else:
            if os.path.isfile(part):
                st.image(part)


WELCOME_MESSAGE = """Welcome to Ultra Trainer! Use the buttons in the sidebar or ask me anything below."""

QUICK_COMMANDS = {
    "Status Overview": """Generate a concise status overview. Do NOT provide any coaching suggestions, recommendations, \
attention points, analysis, or commentary on gaps/strengths. Only present facts.

Include:
1. **Profile**: key athlete details (age, weight, experience, terrain, location) — compact format
2. **Goals**: list upcoming races with date, distance, and goal type
3. **Health**: current injuries/fatigue episodes (or "none")
4. **Weekly volume table**: For the past 10 calendar weeks (Monday-Sunday), show a compact table with:
   - Week dates (Mon-Sun)
   - Total distance (km)
   - Total elevation gain (m)
   Use the weekly_volume tool with week_offset 0 through -9.

Keep it short and factual. No recommendations. No commentary.""",
    "Weekly Progression Chart": """Present a chart for the weekly volume and elevation progression \
for the past 5 weeks and leading up to the training plan end. Use the chart tool with chart_type="weekly_combined". \
Use ISO week format "W13" style for the week labels (not dates).""",
    "Training Plan": """Show the current training plan with all phases and the week-by-week volume table.""",
    "This Week's Plan": """What should I focus on this week? Consider my current training plan phase, \
recent volume, fatigue/injury status, and upcoming goals. Provide specific workout suggestions.""",
}


def build_conversation_context(messages, current_prompt):
    """
    Build conversation context by including recent message history.
    
    Args:
        messages: List of conversation messages
        current_prompt: Current user input
        
    Returns:
        Enhanced prompt with conversation context
    """
    # Get the last few exchanges (excluding the current prompt we just added)
    recent_messages = messages[:-1]  # Exclude the current user message
    
    # Limit to last 6 messages (3 exchanges) to keep context manageable
    if len(recent_messages) > 6:
        recent_messages = recent_messages[-6:]
    
    context_parts = []
    
    # Add recent conversation history
    if len(recent_messages) > 1:  # Only add if there's actual conversation history
        context_parts.append("Recent conversation context:")
        
        for i, msg in enumerate(recent_messages[1:], 1):  # Skip initial greeting
            role = "User" if msg["role"] == "user" else "Coach"
            # Truncate long messages for context
            content = msg["content"][:1000] + "..." if len(msg["content"]) > 1000 else msg["content"]
            context_parts.append(f"{role}: {content}")
        
        context_parts.append("")  # Empty line separator
    
    # Add current question
    context_parts.append(f"Current question: {current_prompt}")
    
    return "\n".join(context_parts)


def generate_and_save_summary(messages, session_id, started_at):
    """Generate short and long summaries of the conversation and save to DB."""
    # Filter to actual conversation (skip greeting if only message)
    convo_messages = [m for m in messages if not (m["role"] == "assistant" and m == messages[0])]
    if len(convo_messages) < 2:
        return  # Nothing meaningful to summarize

    # Build transcript
    transcript_lines = []
    for msg in convo_messages:
        role = "Athlete" if msg["role"] == "user" else "Coach"
        content = msg["content"][:500]
        transcript_lines.append(f"{role}: {content}")
    transcript = "\n".join(transcript_lines)

    turn_count = sum(1 for m in convo_messages if m["role"] == "user")

    try:
        llm = initialize_llm()

        short_resp = llm.invoke(
            f"Summarize this coaching conversation in 1-2 sentences. Focus on key topics, "
            f"decisions, and advice. Be extremely concise.\n\n{transcript}"
        )
        long_resp = llm.invoke(
            f"Summarize this coaching conversation in a detailed paragraph. Include: topics discussed, "
            f"advice given, athlete state, and any action items or follow-ups.\n\n{transcript}"
        )

        store = ContextStore()
        store.save_conversation_summary(
            session_id=session_id,
            summary_short=short_resp.content.strip(),
            summary_long=long_resp.content.strip(),
            started_at=started_at,
            ended_at=datetime.now(timezone.utc),
            turn_count=turn_count,
        )
    except Exception as e:
        st.warning(f"Could not save conversation summary: {e}")


def initialize_agent():
    """Initialize the training agent."""
    try:
        return get_agent()
    except Exception as e:
        st.error(f"Failed to initialize agent: {e}")
        st.error("Please check your environment variables and configuration.")
        return None


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Ultra Trainer - AI Running Coach",
        page_icon="🏃‍♂️",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # Header
    st.title("🏃‍♂️ Ultra Trainer")
    st.subheader("Your AI Ultra Marathon Training Coach")
    
    # Check environment variables
    required_vars = ['OPENAI_API_KEY', 'STRAVA_CLIENT_ID', 'STRAVA_CLIENT_SECRET', 'STRAVA_REFRESH_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        st.error("Please set up your .env file with the required credentials.")
        st.stop()
    
    # Initialize agent
    if "agent" not in st.session_state:
        with st.spinner("Initializing AI coach..."):
            st.session_state.agent = initialize_agent()
            if st.session_state.agent is None:
                st.stop()
    
    # Initialize session tracking
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.session_started_at = datetime.now(timezone.utc)

    # Initialize chat history with welcome message
    if "messages" not in st.session_state:
        store = ContextStore()
        st.session_state.conversation_history = store.get_conversation_history(max_entries=10)
        st.session_state.messages = [
            {"role": "assistant", "content": WELCOME_MESSAGE}
        ]
        st.session_state.pending_command = None
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            render_message(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask your coach anything..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        
        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Coach is thinking..."):
                try:
                    # Build conversation context for the agent
                    enhanced_prompt = build_conversation_context(st.session_state.messages, prompt)

                    # Inject previous session history if available
                    history = getattr(st.session_state, 'conversation_history', '')
                    if history:
                        enhanced_prompt = f"{history}\n\n{enhanced_prompt}"
                    
                    response = st.session_state.agent.invoke({"input": enhanced_prompt})
                    agent_output = response.get("output", "I'm sorry, I couldn't process that request.")
                    render_message(agent_output)
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({"role": "assistant", "content": agent_output})
                    
                except Exception as e:
                    error_msg = f"I encountered an error: {e}. Please try again or check your configuration."
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    # Sidebar with quick commands
    with st.sidebar:
        st.header("Quick Commands")
        for label in QUICK_COMMANDS:
            if st.button(label, use_container_width=True):
                st.session_state.pending_command = label
                st.rerun()

        st.divider()
        if st.button("Clear Chat", use_container_width=True):
            # Save conversation summary before clearing
            if len(st.session_state.messages) > 1:
                with st.spinner("Saving conversation summary..."):
                    generate_and_save_summary(
                        st.session_state.messages,
                        st.session_state.session_id,
                        st.session_state.session_started_at,
                    )

            # Reset session
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.session_started_at = datetime.now(timezone.utc)
            del st.session_state["messages"]
            st.rerun()

    # Process pending quick command
    pending = st.session_state.get("pending_command")
    if pending and pending in QUICK_COMMANDS:
        st.session_state.pending_command = None
        prompt = QUICK_COMMANDS[pending]
        st.session_state.messages.append({"role": "user", "content": pending})
        with st.chat_message("user"):
            st.write(pending)
        with st.chat_message("assistant"):
            with st.spinner("Coach is thinking..."):
                try:
                    enhanced_prompt = build_conversation_context(st.session_state.messages, prompt)
                    history = getattr(st.session_state, 'conversation_history', '')
                    if history:
                        enhanced_prompt = f"{history}\n\n{enhanced_prompt}"
                    response = st.session_state.agent.invoke({"input": enhanced_prompt})
                    agent_output = response.get("output", "I'm sorry, I couldn't process that request.")
                    render_message(agent_output)
                    st.session_state.messages.append({"role": "assistant", "content": agent_output})
                except Exception as e:
                    error_msg = f"I encountered an error: {e}. Please try again or check your configuration."
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})


if __name__ == "__main__":
    main()
