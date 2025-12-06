import pytest

from orbit_remote_mcp.tools.openweather import OpenWeatherTools


@pytest.mark.asyncio
async def test_openweather_tool_lists():
    tools = await OpenWeatherTools().list_tools()
    assert any(tool.name == "current_weather" for tool in tools)
