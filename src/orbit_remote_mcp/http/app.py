"""HTTP application factory."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ..auth.middleware import (
    AuthMiddleware,
    BodySizeLimitMiddleware,
    PUBLIC_PATHS,
    RateLimitMiddleware,
    RequestContextMiddleware,
    issue_session_token,
)
from ..config import Settings
from ..discovery import discover_tool_handlers
from ..logging import get_logger

logger = get_logger(__name__)


def build_app(
    server,
    settings: Settings,
    tool_schemas: List[Dict[str, Any]],
) -> Starlette:
    # Use FastMCP's Starlette app directly so its lifespan initializes the session manager
    app: Starlette = server.streamable_http_app()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=settings.max_body_bytes)
    app.add_middleware(RateLimitMiddleware, limit_per_minute=settings.rate_limit)
    app.add_middleware(AuthMiddleware, settings=settings)

    async def healthcheck(request: Request):
        return JSONResponse({"status": "ok"})

    async def readiness(request: Request):
        return JSONResponse({"status": "ready"})

    async def create_session(request: Request):
        if settings.require_auth and not settings.auth_key:
            raise HTTPException(status_code=500, detail="Auth key not configured")

        api_key = request.headers.get("Authorization") or request.headers.get("X-API-Key")
        valid = False
        if api_key:
            if api_key.lower().startswith("bearer "):
                api_key = api_key.split(" ", 1)[1]
            valid = api_key == settings.auth_key

        if settings.require_auth and not valid:
            raise HTTPException(status_code=401, detail="Invalid API key")

        token = issue_session_token(settings.auth_key or "", settings.session_ttl_seconds)
        return JSONResponse({"session_token": token, "expires_in": settings.session_ttl_seconds})

    async def list_tools(request: Request):
        return JSONResponse({"tools": tool_schemas})

    async def well_known(request: Request):
        base = str(request.base_url).rstrip("/")
        return JSONResponse({
            "mcp": {
                "name": settings.server_name,
                "version": "0.1.0",
                "endpoints": {
                    "mcp": f"{base}/mcp",
                    "health": f"{base}/diagnostics/healthcheck",
                    "tools": f"{base}/tools",
                    "sessions": f"{base}/sessions",
                },
            }
        })

    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception", exc_info=exc)
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

    # Compatibility endpoint for JSON-RPC over HTTP (bypasses FastMCP's Accept strictness)
    tool_handlers = discover_tool_handlers(settings.modules)

    async def mcp_compat(request: Request):
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

        method = payload.get("method")
        rpc_id = payload.get("id")
        params = payload.get("params", {}) or {}

        if method == "tools/list":
            all_tools: list[dict[str, Any]] = []
            for handler in tool_handlers:
                try:
                    tools = await handler.list_tools()
                    for tool in tools:
                        all_tools.append(
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "inputSchema": getattr(tool, "inputSchema", None),
                            }
                        )
                except Exception as exc:
                    logger.warning("List tools failed for %s: %s", handler.__class__.__name__, exc)
            return JSONResponse({"jsonrpc": "2.0", "id": rpc_id, "result": {"tools": all_tools}})

        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {}) or {}
            for handler in tool_handlers:
                try:
                    result = await handler.call_tool(name, arguments)
                    serializable = []
                    if isinstance(result, list):
                        for item in result:
                            if hasattr(item, "text"):
                                serializable.append({"type": "text", "text": item.text})
                            else:
                                serializable.append({"type": "text", "text": str(item)})
                    else:
                        serializable.append({"type": "text", "text": str(result)})
                    return JSONResponse(
                        {
                            "jsonrpc": "2.0",
                            "id": rpc_id,
                            "result": {"content": serializable, "isError": False},
                        }
                    )
                except ValueError:
                    continue
                except Exception as exc:
                    logger.warning("Tool call failed for %s: %s", name, exc)
                    continue
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "error": {"code": -32601, "message": f"Tool {name} not found"},
                },
                status_code=404,
            )

        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": -32601, "message": f"Method {method} not supported"},
            },
            status_code=400,
        )

    app.router.routes.insert(0, Route("/mcp", mcp_compat, methods=["POST"]))
    app.router.routes.insert(1, Route("/mcp/", mcp_compat, methods=["POST"]))

    app.add_route("/diagnostics/healthcheck", healthcheck, methods=["GET"])
    app.add_route("/diagnostics/ready", readiness, methods=["GET"])
    app.add_route("/sessions", create_session, methods=["POST"])
    app.add_route("/tools", list_tools, methods=["GET"])
    app.add_route("/.well-known/mcp.json", well_known, methods=["GET"])
    app.add_exception_handler(Exception, unhandled_exception_handler)

    return app
