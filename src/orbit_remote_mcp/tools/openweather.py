"""OpenWeather-based tool example."""

from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.types import TextContent, Tool

from ..config import Settings
from ..logging import get_logger

logger = get_logger(__name__)


class OpenWeatherTools:
    def __init__(self) -> None:
        settings = Settings()
        self.api_key = settings.openweather_api_key or os.getenv("OPENWEATHER_API_KEY")
        self.base_url = settings.openweather_base_url

    async def list_tools(self) -> list[Tool]:
        return [
            Tool(
                name="current_weather",
                description="Fetch current weather by city (and optional country code)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "City name"},
                        "country": {
                            "type": "string",
                            "description": "ISO 3166 country code (optional)",
                        },
                        "units": {
                            "type": "string",
                            "enum": ["metric", "imperial"],
                            "description": "Units system (default metric)",
                        },
                    },
                    "required": ["city"],
                },
            )
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name != "current_weather":
            raise ValueError(f"Unknown tool: {name}")

        if not self.api_key:
            raise ValueError("OPENWEATHER_API_KEY is not set")

        city = arguments.get("city")
        if not city:
            raise ValueError("city is required")

        country = arguments.get("country")
        units = arguments.get("units", "metric")

        query = city if not country else f"{city},{country}"
        params = {"q": query, "appid": self.api_key, "units": units}

        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            resp = await client.get("/weather", params=params)
            if resp.status_code != 200:
                try:
                    detail = resp.json()
                except Exception:
                    detail = resp.text
                raise ValueError(f"OpenWeather error ({resp.status_code}): {detail}")

            data = resp.json()

        main = data.get("main", {})
        weather = (data.get("weather") or [{}])[0]

        formatted = (
            f"Weather for {data.get('name', query)}:\n"
            f"- Temp: {main.get('temp')}° (feels like {main.get('feels_like')}°)\n"
            f"- Humidity: {main.get('humidity')}%\n"
            f"- Conditions: {weather.get('main')} - {weather.get('description')}\n"
            f"- Wind: {data.get('wind', {}).get('speed')} m/s"
        )

        logger.info("Fetched weather for %s", query)
        return [TextContent(type="text", text=formatted)]

