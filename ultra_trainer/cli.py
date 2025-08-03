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
from ultra_trainer.context_store import ContextStore

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
    'fatigue', 'effort', 'training', 'race', 'recovery', 'nutrition', 'context', 'episodes'
], ignore_case=True)


class UltraTrainerCLI:
    """Interactive CLI for the Ultra Trainer agent."""
    
    def __init__(self):
        """Initialize the CLI."""
        self.agent = None
        self.history = InMemoryHistory()
        self.conversation_context: List[Dict[str, str]] = []
        self.user_profile: Dict[str, str] = {}
        self.context_store = ContextStore()
        
        # Load existing profile from database
        self._load_profile_from_db()
        
    def _load_profile_from_db(self) -> None:
        """Load athlete profile from database."""
        try:
            profile = self.context_store.get_profile()
            if profile:
                # Convert database profile to CLI format
                if profile.get('birth_year'):
                    age = 2025 - profile['birth_year']  # Calculate current age
                    self.user_profile['age'] = str(age)
                
                if profile.get('weight_kg'):
                    self.user_profile['weight'] = str(profile['weight_kg'])
                
                if profile.get('running_years'):
                    self.user_profile['running_years'] = str(profile['running_years'])
                
                if profile.get('preferred_terrain'):
                    self.user_profile['preferred_terrain'] = profile['preferred_terrain']
                
                if profile.get('weekly_mileage_km'):
                    self.user_profile['weekly_mileage'] = f"{profile['weekly_mileage_km']} km"
                
                if profile.get('ultra_experience'):
                    self.user_profile['ultra_experience'] = str(profile['ultra_experience'])
            
            # Load active goals
            goals = self.context_store.get_active_goals()
            if goals:
                goal = goals[0]  # Use first active goal
                self.user_profile['goal_race'] = goal.get('event_name', '')
                if goal.get('event_datetime'):
                    self.user_profile['goal_date'] = goal['event_datetime'][:10]  # YYYY-MM-DD
                if goal.get('fitness_level'):
                    self.user_profile['current_fitness'] = str(goal['fitness_level'])
                    
        except Exception as e:
            self.print_error(f"Warning: Could not load profile from database: {e}")
    
    def _save_profile_to_db(self) -> None:
        """Save current profile to database."""
        try:
            # Convert CLI format to database format
            birth_year = None
            if self.user_profile.get('age'):
                try:
                    birth_year = 2025 - int(self.user_profile['age'])
                except (ValueError, TypeError):
                    pass
            
            weight_kg = None
            if self.user_profile.get('weight'):
                try:
                    weight_kg = float(self.user_profile['weight'])
                except (ValueError, TypeError):
                    pass
            
            running_years = None
            if self.user_profile.get('running_years'):
                try:
                    running_years = int(self.user_profile['running_years'])
                except (ValueError, TypeError):
                    pass
            
            weekly_mileage_km = None
            if self.user_profile.get('weekly_mileage'):
                try:
                    # Extract number from string like "60 km" or "60"
                    mileage_str = self.user_profile['weekly_mileage'].replace('km', '').strip()
                    weekly_mileage_km = float(mileage_str)
                except (ValueError, TypeError):
                    pass
            
            ultra_experience = None
            if self.user_profile.get('ultra_experience'):
                try:
                    ultra_experience = int(self.user_profile['ultra_experience'])
                except (ValueError, TypeError):
                    pass
            
            # Update profile in database
            self.context_store.upsert_profile(
                birth_year=birth_year,
                weight_kg=weight_kg,
                running_years=running_years,
                preferred_terrain=self.user_profile.get('preferred_terrain'),
                weekly_mileage_km=weekly_mileage_km,
                ultra_experience=ultra_experience
            )
            
            # Save goal if exists
            if self.user_profile.get('goal_race'):
                from datetime import datetime
                event_datetime = None
                if self.user_profile.get('goal_date'):
                    try:
                        event_datetime = datetime.fromisoformat(self.user_profile['goal_date'])
                    except ValueError:
                        pass
                
                fitness_level = None
                if self.user_profile.get('current_fitness'):
                    try:
                        fitness_level = int(self.user_profile['current_fitness'])
                    except (ValueError, TypeError):
                        pass
                
                self.context_store.add_or_update_goal(
                    event_name=self.user_profile['goal_race'],
                    event_datetime=event_datetime,
                    fitness_level=fitness_level
                )
                
        except Exception as e:
            self.print_error(f"Warning: Could not save profile to database: {e}")
        
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
            ("context", "Show persistent context summary"),
            ("episodes", "Show recent episodes (injury, fatigue, etc.)"),
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
        
        # Save to database
        self._save_profile_to_db()
        
        return f"I want to train for a {goal_race} in {goal_date}. My current fitness level is {current_fitness}/10, I'm running {weekly_mileage} per week, and I've completed {experience} ultras. Please analyze my recent Strava activities and create a personalized training plan."
    
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
        
        # Save to database
        self._save_profile_to_db()
        
        profile_summary = f"My profile: {age} years old, {weight}kg, {running_years} years of running experience, prefers {preferred_terrain} running."
        return f"{profile_summary} Please take this into account for future recommendations and analyze my recent training."
    
    def handle_injury_command(self) -> str:
        """Handle the injury command."""
        injury_status = prompt("Do you currently have any injuries? (yes/no): ")
        
        if injury_status.lower() in ['yes', 'y']:
            injury_details = prompt("Please describe your injury and current status: ")
            pain_level = prompt("Pain level (0-10): ")
            
            # Log injury episode to database
            try:
                severity = int(pain_level) if pain_level.isdigit() else None
                self.context_store.log_episode(
                    topic="injury",
                    narrative=injury_details,
                    severity=severity
                )
            except Exception as e:
                self.print_error(f"Warning: Could not save injury episode: {e}")
            
            return f"I currently have an injury: {injury_details}. Pain level is {pain_level}/10. Please provide guidance on training modifications and recovery."
        else:
            return "I'm currently injury-free. Please analyze my training for injury prevention strategies."
    
    def handle_fatigue_command(self) -> str:
        """Handle the fatigue command."""
        fatigue_level = prompt("Current fatigue level (1-10, where 10 is extremely tired): ")
        sleep_quality = prompt("Recent sleep quality (poor/fair/good/excellent): ")
        stress_level = prompt("Current stress level (low/medium/high): ")
        
        # Log fatigue episode to database
        try:
            severity = int(fatigue_level) if fatigue_level.isdigit() else None
            narrative = f"Fatigue level: {fatigue_level}/10, Sleep: {sleep_quality}, Stress: {stress_level}"
            self.context_store.log_episode(
                topic="fatigue",
                narrative=narrative,
                severity=severity
            )
        except Exception as e:
            self.print_error(f"Warning: Could not save fatigue episode: {e}")
        
        return f"My current fatigue level is {fatigue_level}/10, sleep quality is {sleep_quality}, and stress level is {stress_level}. Please analyze my recent training load and provide recovery recommendations."
    
    def handle_effort_command(self) -> str:
        """Handle the effort command."""
        recent_run_effort = prompt("Rate the perceived effort of your last run (1-10): ")
        effort_trend = prompt("How has your effort been trending? (easier/same/harder): ")
        
        # Log effort episode to database
        try:
            severity = int(recent_run_effort) if recent_run_effort.isdigit() else None
            narrative = f"Last run effort: {recent_run_effort}/10, Trend: {effort_trend}"
            self.context_store.log_episode(
                topic="effort",
                narrative=narrative,
                severity=severity
            )
        except Exception as e:
            self.print_error(f"Warning: Could not save effort episode: {e}")
        
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
        elif command == 'context':
            self.show_context_summary()
            return None
        elif command == 'episodes':
            self.show_episodes()
            return None
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
    
    def show_context_summary(self) -> None:
        """Show persistent context summary from database."""
        try:
            context_summary = self.context_store.get_context_summary()
            
            self.print_subheader("📊 Persistent Context Summary:")
            
            # Show profile
            if context_summary.get('profile'):
                profile = context_summary['profile']
                print_formatted_text("<subheader>👤 Profile:</subheader>", style=style)
                if profile.get('birth_year'):
                    age = 2025 - profile['birth_year']
                    print_formatted_text(f"  Age: {age}")
                if profile.get('weight_kg'):
                    print_formatted_text(f"  Weight: {profile['weight_kg']}kg")
                if profile.get('running_years'):
                    print_formatted_text(f"  Running Experience: {profile['running_years']} years")
                if profile.get('preferred_terrain'):
                    print_formatted_text(f"  Preferred Terrain: {profile['preferred_terrain']}")
                if profile.get('weekly_mileage_km'):
                    print_formatted_text(f"  Weekly Mileage: {profile['weekly_mileage_km']}km")
                if profile.get('ultra_experience'):
                    print_formatted_text(f"  Ultra Experience: {profile['ultra_experience']} races")
                print()
            
            # Show goals
            if context_summary.get('active_goals'):
                print_formatted_text("<subheader>🎯 Active Goals:</subheader>", style=style)
                for goal in context_summary['active_goals'][:3]:
                    goal_text = f"  • {goal['event_name']}"
                    if goal.get('distance_km'):
                        goal_text += f" ({goal['distance_km']}km)"
                    if goal.get('event_datetime'):
                        goal_text += f" - {goal['event_datetime'][:10]}"
                    if goal.get('fitness_level'):
                        goal_text += f" (fitness: {goal['fitness_level']}/10)"
                    print_formatted_text(goal_text)
                print()
            
            # Show current episodes
            if context_summary.get('current_episodes'):
                print_formatted_text("<subheader>⚠️  Current Episodes:</subheader>", style=style)
                for episode in context_summary['current_episodes'][:5]:
                    episode_text = f"  • {episode['topic'].title()}"
                    if episode.get('severity'):
                        episode_text += f" (severity: {episode['severity']}/10)"
                    episode_text += f": {episode['narrative_text'][:60]}..."
                    print_formatted_text(episode_text)
                print()
            
        except Exception as e:
            self.print_error(f"Could not load context summary: {e}")
    
    def show_episodes(self) -> None:
        """Show recent episodes from database."""
        try:
            episodes = self.context_store.get_recent_episodes(days=30)
            
            if not episodes:
                self.print_system("No episodes recorded in the last 30 days.")
                return
            
            self.print_subheader("📋 Recent Episodes (last 30 days):")
            
            # Group by topic
            topics = {}
            for episode in episodes:
                topic = episode['topic']
                if topic not in topics:
                    topics[topic] = []
                topics[topic].append(episode)
            
            for topic, topic_episodes in topics.items():
                print_formatted_text(f"<subheader>{topic.title()}:</subheader>", style=style)
                for episode in topic_episodes[:3]:  # Show max 3 per topic
                    status = "Ongoing" if not episode.get('end_date') else "Resolved"
                    severity_text = f" (severity: {episode['severity']}/10)" if episode.get('severity') else ""
                    date_text = episode['start_date'][:10] if episode.get('start_date') else "Unknown"
                    
                    print_formatted_text(f"  • [{status}] {date_text}{severity_text}")
                    print_formatted_text(f"    {episode['narrative_text'][:80]}...")
                print()
                
        except Exception as e:
            self.print_error(f"Could not load episodes: {e}")
    
    def add_context_to_prompt(self, user_input: str) -> str:
        """Add context to the user prompt using database and conversation history."""
        context_parts = []
        
        # Add user profile context from database
        try:
            context_summary = self.context_store.get_context_summary()
            
            # Add profile information
            if context_summary.get('profile'):
                profile = context_summary['profile']
                profile_items = []
                if profile.get('birth_year'):
                    age = 2025 - profile['birth_year']
                    profile_items.append(f"age: {age}")
                if profile.get('weight_kg'):
                    profile_items.append(f"weight: {profile['weight_kg']}kg")
                if profile.get('running_years'):
                    profile_items.append(f"running experience: {profile['running_years']} years")
                if profile.get('preferred_terrain'):
                    profile_items.append(f"preferred terrain: {profile['preferred_terrain']}")
                if profile.get('weekly_mileage_km'):
                    profile_items.append(f"weekly mileage: {profile['weekly_mileage_km']}km")
                if profile.get('ultra_experience'):
                    profile_items.append(f"ultra experience: {profile['ultra_experience']} races")
                
                if profile_items:
                    context_parts.append(f"My profile: {' | '.join(profile_items)}")
            
            # Add active goals
            if context_summary.get('active_goals'):
                goals = context_summary['active_goals']
                for goal in goals[:2]:  # Limit to 2 most recent goals
                    goal_info = f"Goal: {goal['event_name']}"
                    if goal.get('distance_km'):
                        goal_info += f" ({goal['distance_km']}km)"
                    if goal.get('event_datetime'):
                        goal_info += f" on {goal['event_datetime'][:10]}"
                    if goal.get('fitness_level'):
                        goal_info += f" (current fitness: {goal['fitness_level']}/10)"
                    context_parts.append(goal_info)
            
            # Add current episodes (injuries, fatigue, etc.)
            if context_summary.get('current_episodes'):
                episodes = context_summary['current_episodes']
                for episode in episodes[:3]:  # Limit to 3 most recent
                    episode_info = f"Current {episode['topic']}"
                    if episode.get('severity'):
                        episode_info += f" (severity: {episode['severity']}/10)"
                    episode_info += f": {episode['narrative_text'][:50]}..."
                    context_parts.append(episode_info)
        
        except Exception as e:
            # Fallback to in-memory profile if database fails
            if self.user_profile:
                profile_str = " | ".join([f"{k}: {v}" for k, v in self.user_profile.items() if v])
                context_parts.append(f"My profile: {profile_str}")
        
        # Add recent conversation context from memory (keep this for immediate context)
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
            
            # Store in conversation context (memory)
            self.conversation_context.append({
                "user": user_input,
                "agent": agent_output
            })
            
            # Store in database
            try:
                self.context_store.add_convo_turn("user", user_input)
                self.context_store.add_convo_turn("agent", agent_output)
            except Exception as e:
                self.print_error(f"Warning: Could not save conversation to database: {e}")
            
            # Keep only last 10 exchanges in memory to manage memory
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
