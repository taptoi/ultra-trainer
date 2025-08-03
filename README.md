# ultra-trainer
AI-powered ultra marathon training assistant with Strava integration

An intelligent coaching system that analyzes your Strava activities and provides personalized training advice for ultra marathon preparation. Features persistent memory, location-aware recommendations, and evidence-based coaching through a conversational web interface.

## Development

This project uses [Poetry](https://python-poetry.org/) for dependency management.

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Set up Strava API access:
   - Create a Strava API application at https://www.strava.com/settings/api
   - Note your Client ID and Client Secret
   - Run the token helper script:
     ```bash
     poetry run python get_strava_token.py
     ```
   - Follow the prompts to authorize the application and get your tokens
   - The script will automatically create/update your `.env` file with the required credentials

   Required Strava API scopes: `read`, `activity:read`, `activity:read_all`, `profile:read_all`

3. Set up OpenAI API access:
   - Get an API key from https://platform.openai.com/
   - Add it to your `.env` file:
     ```
     OPENAI_API_KEY=your_api_key_here
     OPENAI_MODEL=gpt-4o
     ```
   - The system supports various OpenAI models including GPT-4o, GPT-4, and o3

## Features

- **Persistent Memory**: Your athlete profile, goals, injuries, and conversation history are stored locally in SQLite
- **Strava Integration**: Automatic analysis of your training activities, including heart rate, pace, and elevation data
- **Location Awareness**: Workout recommendations adapted to your current location and local time
- **Health Tracking**: Log and track injuries, fatigue levels, and perceived effort over time
- **Goal Management**: Set and track progress toward specific races and training objectives
- **Evidence-Based Coaching**: Detailed, surgical approach to training recommendations based on sports science
- **Multi-Turn Conversations**: Natural dialogue that remembers context across sessions

## Usage

### Interactive Web Interface

Start the Streamlit web interface for an interactive coaching session:

```bash
poetry run streamlit run ultra_trainer/app.py
```

The web interface provides:
- Multi-turn conversations with an AI ultra marathon coach
- Analysis of your Strava training data
- Personalized coaching advice and training plans
- Persistent memory of your profile, goals, injuries, and previous discussions
- Location and time-aware workout recommendations
- Natural language interaction without strict command syntax

### Example Prompts

Here are some useful prompts to get started with your ultra marathon training assistant:

**Initial Setup & Profile:**
```
"Could you help me set up my athlete profile? I'm 35 years old, weigh 70kg, have been running for 8 years, and live in Copenhagen, Denmark."

"Could you please list my current goals?"
```

**Continuing Previous Conversations:**
```
"Could you follow-up the previous conversations, and continue your athlete check-up with me from where we were left last time?"

"What did we discuss in our last conversation about my training plan?"
```

**Logging Health Episodes:**
```
"I seem to experience a mild shin splint on my right leg since yesterday. Could you log this as an injury, severity 4?"

"I'm feeling quite fatigued today after yesterday's long run. Can you log this as a fatigue episode with severity 6?"

"Today's tempo run felt really good, I'd rate the effort as 7/10. Please log this."
```

**Training Analysis & Recommendations:**
```
"Please analyze all the activities from last three weeks and suggest recommendations to improve my hill-endurance and to maintain a low heart rate in technical terrain?"

"Can you analyze my recent training consistency and suggest what I should focus on this week?"

"I have a 50K trail race in 8 weeks. Can you create a training plan based on my recent activities?"
```

**Workout Recommendations:**
```
"What workout should I do today? I'm in Copenhagen and it's currently evening."

"Can you suggest a hill training session for tomorrow morning?"

"I want to work on my base endurance. What should I do this week?"
```

**Goal Setting:**
```
"I want to run the Western States 100 in June 2026. Can you help me set this as a goal?"

"Can you remove my old 50K goal and add a new marathon goal for next spring?"
```

### Strava MCP server

This project bundles a Strava MCP server adapted from [tomekkorbak/strava-mcp-server](https://github.com/tomekkorbak/strava-mcp-server) under the MIT license. It can be started locally with:

```bash
poetry run strava-mcp-server
```

The server exposes tools such as `get_recent_activities` for integration with language models.

## Data Storage

The application stores your training data locally in an SQLite database (`ultra_trainer.db`) which includes:

- **Athlete Profile**: Age, weight, experience level, preferred terrain, current/default location
- **Training Goals**: Target races, distances, dates, and time goals
- **Health Episodes**: Injuries, fatigue levels, and perceived effort logs with severity ratings
- **Conversation History**: Previous coaching discussions for continuity across sessions

All data remains on your local machine and is not shared externally. The database file is excluded from version control for privacy.
