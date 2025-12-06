"""Sample resource handler."""

from __future__ import annotations

from typing import Any, List

from ..logging import get_logger

logger = get_logger(__name__)


class SampleResourceHandler:
    async def list_resources(self) -> List[dict[str, Any]]:
        return [
            {"name": "status", "uri": "local://status", "description": "Static status resource"},
        ]

    async def get_resource(self, resource_id: str, params: dict[str, Any]) -> Any:
        if resource_id != "status":
            raise ValueError(f"Unknown resource: {resource_id}")
        return {"status": "ok", "params": params}
