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

## Strava MCP server

This project bundles a Strava MCP server adapted from [tomekkorbak/strava-mcp-server](https://github.com/tomekkorbak/strava-mcp-server) under the MIT license. It can be started locally with:

```bash
poetry run strava-mcp-server
```

The server exposes tools such as `get_recent_activities` for integration with language models.
