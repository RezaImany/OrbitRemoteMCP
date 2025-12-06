"""Protocols defining handler contracts."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from mcp.types import Tool


@runtime_checkable
class ToolHandler(Protocol):
    async def list_tools(self) -> list[Tool]:
        ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        ...


@runtime_checkable
class ResourceHandler(Protocol):
    async def list_resources(self) -> list[Any]:
        ...

    async def get_resource(self, resource_id: str, params: dict[str, Any]) -> Any:
        ...


def is_tool_handler(obj: object) -> bool:
    return isinstance(obj, ToolHandler)


def is_resource_handler(obj: object) -> bool:
    return isinstance(obj, ResourceHandler)

