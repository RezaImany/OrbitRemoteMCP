import pytest

from orbit_remote_mcp.discovery import discover_tool_handlers


def test_discovery_loads_openweather():
    handlers = discover_tool_handlers(["orbit_remote_mcp.tools.openweather"])
    assert handlers, "Expected at least one handler"
