# ultra-trainer
Your personal Strava ultra marathon training app

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

## Usage

### Interactive CLI Coach

Start an interactive coaching session:

```bash
poetry run ultra-trainer
```

The CLI provides:
- Multi-turn conversations with an AI ultra marathon coach
- Analysis of your Strava training data
- Personalized coaching advice and training plans
- Interactive commands for setting goals, reporting fatigue, injuries, etc.
- Context-aware conversations that remember your profile and previous discussions

Available commands in the CLI:
- `goals` - Set your training goals and target races
- `profile` - Update your athlete profile
- `injury` - Report or discuss injuries
- `fatigue` - Discuss fatigue and recovery status
- `effort` - Report perceived effort levels
- `help` - Show all available commands

### Strava MCP server

This project bundles a Strava MCP server adapted from [tomekkorbak/strava-mcp-server](https://github.com/tomekkorbak/strava-mcp-server) under the MIT license. It can be started locally with:

```bash
poetry run strava-mcp-server
```

The server exposes tools such as `get_recent_activities` for integration with language models.
