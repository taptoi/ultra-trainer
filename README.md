# ultra-trainer
Your personal Strava ultra marathon training app

## Development

This project uses [Poetry](https://python-poetry.org/) for dependency management.

1. Install dependencies:
   ```bash
   poetry install
   ```
2. Create a `.env` file based on `.env.template` and fill in the required values.

## Strava MCP server

This project bundles a Strava MCP server adapted from [tomekkorbak/strava-mcp-server](https://github.com/tomekkorbak/strava-mcp-server) under the MIT license. It can be started locally with:

```bash
poetry run strava-mcp-server
```

The server exposes tools such as `get_recent_activities` for integration with language models.
