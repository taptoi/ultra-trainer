#!/usr/bin/env python3
"""
Streamlit Web Interface for Ultra Trainer

This module provides a web-based chat interface for the ultra marathon training agent.
It provides a simple multi-turn conversation interface without persistent storage
or special commands for now.
"""

import os
import streamlit as st
from dotenv import load_dotenv

from ultra_trainer.agent import get_agent

# Load environment variables
load_dotenv()


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
            content = msg["content"][:200] + "..." if len(msg["content"]) > 200 else msg["content"]
            context_parts.append(f"{role}: {content}")
        
        context_parts.append("")  # Empty line separator
    
    # Add current question
    context_parts.append(f"Current question: {current_prompt}")
    
    return "\n".join(context_parts)


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
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hi! I'm your ultra marathon training coach. I can analyze your Strava data and provide personalized advice. Tell me about your training goals and current situation!"
            }
        ]
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
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
                    
                    response = st.session_state.agent.invoke({"input": enhanced_prompt})
                    agent_output = response.get("output", "I'm sorry, I couldn't process that request.")
                    st.write(agent_output)
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({"role": "assistant", "content": agent_output})
                    
                except Exception as e:
                    error_msg = f"I encountered an error: {e}. Please try again or check your configuration."
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    # Sidebar with info
    with st.sidebar:
        st.header("About")
        st.write("This is your personal ultra marathon training assistant powered by AI and Strava data.")
        
        st.header("Features")
        st.write("• Analyzes your Strava activities")
        st.write("• Provides personalized coaching advice")
        st.write("• Answers training questions")
        st.write("• Helps with race preparation")
        
        if st.button("Clear Chat"):
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": "Hi! I'm your ultra marathon training coach. I can analyze your Strava data and provide personalized advice. Tell me about your training goals and current situation!"
                }
            ]
            st.rerun()


if __name__ == "__main__":
    main()
