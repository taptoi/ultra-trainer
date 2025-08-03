import asyncio

from ultra_trainer.strava_mcp_server import server


class DummyStravaClient:
    def get_activities(self, limit: int = 10, before: int | None = None, after: int | None = None):
        return [{"name": "Morning Run"}]


def test_get_recent_activities_returns_data():
    server.strava_client = DummyStravaClient()
    blocks, payload = asyncio.run(
        server.mcp.call_tool("get_recent_activities", {"days": 1, "limit": 1})
    )
    assert payload["data"][0]["name"] == "Morning Run"
