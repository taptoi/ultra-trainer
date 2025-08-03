import asyncio
import logging
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ultra_trainer.strava_mcp_server import server


@pytest.mark.integration
def test_get_activities_returns_data() -> None:
    refresh_token = os.getenv("STRAVA_REFRESH_TOKEN")
    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")

    missing = [
        name
        for name, value in [
            ("STRAVA_REFRESH_TOKEN", refresh_token),
            ("STRAVA_CLIENT_ID", client_id),
            ("STRAVA_CLIENT_SECRET", client_secret),
        ]
        if not value
    ]

    if missing:
        error_message = f"Strava credentials not configured: missing {', '.join(missing)}"
        logging.error("Missing Strava env vars: %s", ", ".join(missing))
        pytest.fail(error_message)

    # Initialize the Strava client and let it handle token refresh
    server.strava_client = server.StravaClient(
        refresh_token, client_id, client_secret
    )
    # Don't manually set access_token and expires_at - let the client refresh automatically

    blocks, payload = asyncio.run(
        server.mcp.call_tool("get_activities", {"limit": 1})
    )

    if "error" in payload:
        pytest.fail(f"Strava API error: {payload['error']}")

    assert "data" in payload
    assert isinstance(payload["data"], list)
