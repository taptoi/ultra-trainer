import asyncio
import logging
import os
import time
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
    access_token = os.getenv("STRAVA_ACCESS_TOKEN")

    missing = [
        name
        for name, value in [
            ("STRAVA_REFRESH_TOKEN", refresh_token),
            ("STRAVA_CLIENT_ID", client_id),
            ("STRAVA_CLIENT_SECRET", client_secret),
            ("STRAVA_ACCESS_TOKEN", access_token),
        ]
        if not value
    ]

    if missing:
        skip_reason = f"Strava credentials not configured: missing {', '.join(missing)}"
        logging.warning("Missing Strava env vars: %s", ", ".join(missing))
        pytest.skip(skip_reason)

    server.strava_client = server.StravaClient(
        refresh_token, client_id, client_secret
    )
    server.strava_client.access_token = access_token
    server.strava_client.expires_at = int(time.time()) + 3600

    blocks, payload = asyncio.run(
        server.mcp.call_tool("get_activities", {"limit": 1})
    )

    if "error" in payload:
        pytest.skip(f"Strava API error: {payload['error']}")

    assert "data" in payload
    assert isinstance(payload["data"], list)
