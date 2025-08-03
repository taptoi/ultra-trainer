# Adapted from https://github.com/tomekkorbak/strava-mcp-server
# Licensed under the MIT License.
"""Strava MCP Server package."""

from .server import main

__all__ = ["main"]


def hello() -> str:
    return "Hello from strava-mcp-server!"
