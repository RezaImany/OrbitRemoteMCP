"""FastMCP server wiring."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from mcp.server import FastMCP

from ..config import Settings
from ..discovery import discover_resource_handlers, discover_tool_handlers
from ..logging import get_logger

logger = get_logger(__name__)


async def _register_tools(server: FastMCP, handlers: list[Any]) -> List[Dict[str, Any]]:
    tool_schemas: List[Dict[str, Any]] = []
    for handler in handlers:
        try:
            tools = await handler.list_tools()
        except Exception as exc:
            logger.warning("Failed to list tools from %s: %s", handler.__class__.__name__, exc)
            continue

        for tool in tools:
            tool_schemas.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": getattr(tool, "inputSchema", None),
                }
            )

            async def wrapper(**kwargs):
                logger.info("Calling tool %s with %s", tool.name, kwargs)
                return await handler.call_tool(tool.name, kwargs)

            wrapper.__name__ = tool.name
            wrapper.__doc__ = tool.description
            server.tool(name=tool.name, description=tool.description)(wrapper)
    return tool_schemas


async def _register_resources(server: FastMCP, handlers: list[Any]) -> None:
    if not hasattr(server, "resource"):
        logger.warning("FastMCP resource decorator not available; skipping resources")
        return

    for handler in handlers:
        try:
            resources = await handler.list_resources()
        except Exception as exc:
            logger.warning("Failed to list resources from %s: %s", handler.__class__.__name__, exc)
            continue

        for resource in resources:
            resource_name = None
            if isinstance(resource, dict):
                resource_name = resource.get("name") or resource.get("id")
                resource_uri = resource.get("uri") or resource_name
                description = resource.get("description")
            else:
                resource_name = getattr(resource, "name", None) or getattr(resource, "id", None)
                resource_uri = getattr(resource, "uri", None) or resource_name
                description = getattr(resource, "description", None)

            if not resource_name or not resource_uri:
                continue

            if "://" not in resource_uri:
                resource_uri = f"local://{resource_uri}"

            async def wrapper():
                return await handler.get_resource(resource_name, {})

            wrapper.__name__ = f"resource_{resource_name}"
            server.resource(uri=resource_uri, name=resource_name, description=description)(wrapper)


def build_server(settings: Settings):
    server = FastMCP(settings.server_name)

    tool_handlers = discover_tool_handlers(settings.modules)
    resource_handlers = discover_resource_handlers(settings.modules)

    tool_schemas = asyncio.run(_register_tools(server, tool_handlers))
    if resource_handlers:
        asyncio.run(_register_resources(server, resource_handlers))

    @server.tool(name="health", description="Health check")
    async def health():
        return "ok"

    return server, tool_schemas
