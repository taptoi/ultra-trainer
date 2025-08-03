#!/usr/bin/env python3
"""
CLI Chat Interface for Ultra Trainer

This module provides an interactive command-line interface for multi-turn conversations
with the ultra marathon training agent. It supports customized coaching sessions where
the AI can ask for user feedback about perceived effort, fatigue, injuries, and training goals.
"""

import os
import sys
from typing import Dict, List, Optional

from dotenv import load_dotenv
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.styles import Style

from ultra_trainer.agent import get_agent

# Load environment variables
load_dotenv()

# CLI style configuration
style = Style.from_dict({
    'user': '#ansiblue bold',
    'agent': '#ansigreen',
    'system': '#ansiyellow',
    'error': '#ansired bold',
    'header': '#ansimagenta bold',
    'subheader': '#ansicyan',
})

# Command completion
command_completer = WordCompleter([
    'help', 'exit', 'quit', 'clear', 'history', 'goals', 'profile', 'injury',
    'fatigue', 'effort', 'training', 'race', 'recovery', 'nutrition'
], ignore_case=True)


class UltraTrainerCLI:
    """Interactive CLI for the Ultra Trainer agent."""
    
    def __init__(self):
        """Initialize the CLI."""
        self.agent = None
        self.history = InMemoryHistory()
        self.conversation_context: List[Dict[str, str]] = []
        self.user_profile: Dict[str, str] = {}
        
    def initialize_agent(self) -> bool:
        """Initialize the training agent."""
        try:
            self.agent = get_agent()
            return True
        except Exception as e:
            self.print_error(f"Failed to initialize agent: {e}")
            return False
    
    def print_header(self, text: str) -> None:
        """Print a formatted header."""
        print_formatted_text(HTML(f'<header>{text}</header>'), style=style)
    
    def print_subheader(self, text: str) -> None:
        """Print a formatted subheader."""
        print_formatted_text(HTML(f'<subheader>{text}</subheader>'), style=style)
    
    def print_user(self, text: str) -> None:
        """Print user input."""
        print_formatted_text(HTML(f'<user>You:</user> {text}'), style=style)
    
    def print_agent(self, text: str) -> None:
        """Print agent response."""
        print_formatted_text(HTML(f'<agent>Coach:</agent> {text}'), style=style)
    
    def print_system(self, text: str) -> None:
        """Print system message."""
        print_formatted_text(HTML(f'<system>System:</system> {text}'), style=style)
    
    def print_error(self, text: str) -> None:
        """Print error message."""
        print_formatted_text(HTML(f'<error>Error:</error> {text}'), style=style)
    
    def show_welcome(self) -> None:
        """Display welcome message."""
        self.print_header("🏃‍♂️ Ultra Trainer - AI Running Coach")
        print()
        print_formatted_text("Welcome to your personal ultra marathon training assistant!")
        print_formatted_text("I can analyze your Strava data and provide personalized coaching advice.")
        print()
        self.print_subheader("Available Commands:")
        print_formatted_text("• Type 'help' for a list of commands")
        print_formatted_text("• Type 'goals' to set your training goals")
        print_formatted_text("• Type 'profile' to update your athlete profile")
        print_formatted_text("• Ask me anything about your training!")
        print()
        print_formatted_text("Let's start by understanding your current situation...")
        print()
    
    def show_help(self) -> None:
        """Display help information."""
        self.print_subheader("Commands:")
        commands = [
            ("help", "Show this help message"),
            ("goals", "Set or update your training goals"),
            ("profile", "Update your athlete profile"),
            ("injury", "Report or discuss injuries"),
            ("fatigue", "Discuss fatigue and recovery"),
            ("effort", "Report perceived effort levels"),
            ("training", "Get training advice"),
            ("race", "Discuss race preparation"),
            ("recovery", "Get recovery recommendations"),
            ("nutrition", "Discuss nutrition strategies"),
            ("history", "Show conversation history"),
            ("clear", "Clear the screen"),
            ("exit/quit", "Exit the application"),
        ]
        
        for cmd, desc in commands:
            print_formatted_text(f"  <subheader>{cmd:12}</subheader> - {desc}", style=style)
        print()
    
    def handle_goals_command(self) -> str:
        """Handle the goals command."""
        print_formatted_text("Let's set up your training goals...")
        
        goal_race = prompt("What's your target race or distance? (e.g., '100K trail race', '50 mile ultra'): ")
        goal_date = prompt("When is your target race? (e.g., 'October 2025', 'Spring 2026'): ")
        current_fitness = prompt("How would you rate your current fitness level (1-10)? ")
        weekly_mileage = prompt("What's your current weekly mileage? ")
        experience = prompt("How many ultras have you completed? ")
        
        self.user_profile.update({
            'goal_race': goal_race,
            'goal_date': goal_date,
            'current_fitness': current_fitness,
            'weekly_mileage': weekly_mileage,
            'ultra_experience': experience
        })
        
        return f"I want to train for a {goal_race} in {goal_date}. My current fitness level is {current_fitness}/10, I'm running {weekly_mileage} miles per week, and I've completed {experience} ultras. Please analyze my recent Strava activities and create a personalized training plan."
    
    def handle_profile_command(self) -> str:
        """Handle the profile command."""
        print_formatted_text("Let's update your athlete profile...")
        
        age = prompt("Age: ", default=self.user_profile.get('age', ''))
        weight = prompt("Weight (kg): ", default=self.user_profile.get('weight', ''))
        running_years = prompt("Years of running experience: ", default=self.user_profile.get('running_years', ''))
        preferred_terrain = prompt("Preferred terrain (road/trail/mixed): ", default=self.user_profile.get('preferred_terrain', ''))
        
        self.user_profile.update({
            'age': age,
            'weight': weight,
            'running_years': running_years,
            'preferred_terrain': preferred_terrain
        })
        
        profile_summary = f"My profile: {age} years old, {weight}kg, {running_years} years of running experience, prefers {preferred_terrain} running."
        return f"{profile_summary} Please take this into account for future recommendations and analyze my recent training."
    
    def handle_injury_command(self) -> str:
        """Handle the injury command."""
        injury_status = prompt("Do you currently have any injuries? (yes/no): ")
        
        if injury_status.lower() in ['yes', 'y']:
            injury_details = prompt("Please describe your injury and current status: ")
            pain_level = prompt("Pain level (0-10): ")
            return f"I currently have an injury: {injury_details}. Pain level is {pain_level}/10. Please provide guidance on training modifications and recovery."
        else:
            return "I'm currently injury-free. Please analyze my training for injury prevention strategies."
    
    def handle_fatigue_command(self) -> str:
        """Handle the fatigue command."""
        fatigue_level = prompt("Current fatigue level (1-10, where 10 is extremely tired): ")
        sleep_quality = prompt("Recent sleep quality (poor/fair/good/excellent): ")
        stress_level = prompt("Current stress level (low/medium/high): ")
        
        return f"My current fatigue level is {fatigue_level}/10, sleep quality is {sleep_quality}, and stress level is {stress_level}. Please analyze my recent training load and provide recovery recommendations."
    
    def handle_effort_command(self) -> str:
        """Handle the effort command."""
        recent_run_effort = prompt("Rate the perceived effort of your last run (1-10): ")
        effort_trend = prompt("How has your effort been trending? (easier/same/harder): ")
        
        return f"My last run felt like a {recent_run_effort}/10 effort, and training has been feeling {effort_trend} lately. Please analyze this in context of my recent Strava data."
    
    def handle_command(self, user_input: str) -> Optional[str]:
        """Handle special commands."""
        command = user_input.lower().strip()
        
        if command in ['help', 'h']:
            self.show_help()
            return None
        elif command == 'goals':
            return self.handle_goals_command()
        elif command == 'profile':
            return self.handle_profile_command()
        elif command == 'injury':
            return self.handle_injury_command()
        elif command == 'fatigue':
            return self.handle_fatigue_command()
        elif command == 'effort':
            return self.handle_effort_command()
        elif command == 'history':
            self.show_conversation_history()
            return None
        elif command == 'clear':
            os.system('clear' if os.name == 'posix' else 'cls')
            return None
        elif command in ['exit', 'quit', 'q']:
            self.print_system("Thanks for training with Ultra Trainer! Keep running! 🏃‍♂️")
            sys.exit(0)
        
        return user_input
    
    def show_conversation_history(self) -> None:
        """Show conversation history."""
        if not self.conversation_context:
            self.print_system("No conversation history yet.")
            return
        
        self.print_subheader("Conversation History:")
        for i, exchange in enumerate(self.conversation_context[-5:], 1):  # Show last 5 exchanges
            print_formatted_text(f"<user>{i}. You:</user> {exchange['user']}", style=style)
            print_formatted_text(f"<agent>   Coach:</agent> {exchange['agent'][:100]}...", style=style)
        print()
    
    def add_context_to_prompt(self, user_input: str) -> str:
        """Add context to the user prompt."""
        context_parts = []
        
        # Add user profile context
        if self.user_profile:
            profile_str = " | ".join([f"{k}: {v}" for k, v in self.user_profile.items() if v])
            context_parts.append(f"My profile: {profile_str}")
        
        # Add recent conversation context
        if self.conversation_context:
            recent_context = self.conversation_context[-2:]  # Last 2 exchanges
            for exchange in recent_context:
                context_parts.append(f"Previous: User asked '{exchange['user']}', you responded about {exchange['agent'][:50]}...")
        
        if context_parts:
            context = "\n".join(context_parts)
            return f"{context}\n\nCurrent question: {user_input}"
        
        return user_input
    
    def get_agent_response(self, user_input: str) -> str:
        """Get response from the agent."""
        try:
            # Add context to the prompt
            enhanced_prompt = self.add_context_to_prompt(user_input)
            
            # Get agent response
            response = self.agent.invoke({"input": enhanced_prompt})
            agent_output = response.get("output", "I'm sorry, I couldn't process that request.")
            
            # Store in conversation context
            self.conversation_context.append({
                "user": user_input,
                "agent": agent_output
            })
            
            # Keep only last 10 exchanges to manage memory
            if len(self.conversation_context) > 10:
                self.conversation_context = self.conversation_context[-10:]
            
            return agent_output
            
        except Exception as e:
            return f"I encountered an error: {e}. Please try again or check your configuration."
    
    def suggest_follow_up_questions(self) -> None:
        """Suggest relevant follow-up questions."""
        if len(self.conversation_context) % 3 == 0:  # Every 3rd interaction
            suggestions = [
                "How are you feeling about your current training load?",
                "Do you have any concerns about upcoming workouts?",
                "Would you like me to analyze your recovery patterns?",
                "Are there any specific areas you'd like to focus on?"
            ]
            
            self.print_subheader("💡 Suggested questions:")
            for suggestion in suggestions[:2]:  # Show 2 suggestions
                print_formatted_text(f"  • {suggestion}")
            print()
    
    def run(self) -> None:
        """Run the main CLI loop."""
        # Check environment variables
        required_vars = ['OPENAI_API_KEY', 'STRAVA_CLIENT_ID', 'STRAVA_CLIENT_SECRET', 'STRAVA_REFRESH_TOKEN']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            self.print_error(f"Missing required environment variables: {', '.join(missing_vars)}")
            self.print_system("Please set up your .env file with the required credentials.")
            return
        
        # Initialize agent
        if not self.initialize_agent():
            return
        
        # Show welcome message
        self.show_welcome()
        
        # Initial coaching prompt
        initial_prompt = ("Hi! I'm your ultra marathon training coach. I can analyze your Strava data and provide "
                         "personalized advice. To get started, could you tell me about your training goals and "
                         "current situation? Or use 'goals' command to set up your profile.")
        
        self.print_agent(initial_prompt)
        print()
        
        # Main chat loop
        while True:
            try:
                # Get user input
                user_input = prompt(
                    HTML('<user>You:</user> '),
                    style=style,
                    history=self.history,
                    completer=command_completer,
                    complete_style='column'
                ).strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                processed_input = self.handle_command(user_input)
                if processed_input is None:
                    continue
                
                # Get and display agent response
                print()  # Empty line for readability
                agent_response = self.get_agent_response(processed_input)
                self.print_agent(agent_response)
                print()
                
                # Occasionally suggest follow-up questions
                self.suggest_follow_up_questions()
                
            except KeyboardInterrupt:
                print()
                self.print_system("Training session interrupted. Thanks for using Ultra Trainer!")
                break
            except EOFError:
                break


def main() -> None:
    """Main entry point for the CLI."""
    cli = UltraTrainerCLI()
    cli.run()


if __name__ == "__main__":
    main()
