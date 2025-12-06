# Architecture Overview

OrbitRemoteMCP is an HTTP-only, streamable MCP framework with a thin Starlette/FastMCP integration plus compatibility handlers for JSON-RPC over HTTP.

## Components
- **Entry point**: `src/orbit_remote_mcp/__main__.py` – loads env/config, sets logging, builds server, runs uvicorn.
- **Config**: `src/orbit_remote_mcp/config.py` – Pydantic settings; optional `ORBIT_MODULES` for plugins; sensible defaults.
- **Logging**: `src/orbit_remote_mcp/logging.py` – structured logs, request IDs.
- **Discovery**: `src/orbit_remote_mcp/discovery.py` – auto-load built-in tools/resources, optional entrypoints or `ORBIT_MODULES`.
- **Protocols**: `src/orbit_remote_mcp/protocols.py` – lightweight contracts for tool/resource handlers.
- **Auth & guards**: `src/orbit_remote_mcp/auth/middleware.py` – API key + session tokens, rate limiting, body-size limits, CORS, request ID propagation.
- **Server wiring**: `src/orbit_remote_mcp/core/server.py` – builds FastMCP server, registers tools/resources, adds health tool.
- **HTTP app**: `src/orbit_remote_mcp/http/app.py` – wraps the FastMCP app, adds diagnostics, sessions, tools listing, well-known endpoint, and a compatibility `/mcp` JSON-RPC handler (avoids Accept-related 406s).
- **Samples (optional)**: `src/orbit_remote_mcp/tools/openweather.py`, `src/orbit_remote_mcp/resources/sample.py` – reference only; remove when not needed.

## Request flow
1. `uvicorn` -> Starlette app from `server.streamable_http_app()`.
2. Middleware pipeline: CORS -> request ID -> body-size limit -> rate limit -> auth.
3. Routes:
   - Diagnostics: `/diagnostics/healthcheck`, `/diagnostics/ready`
   - Sessions: `/sessions` -> session token issuance
   - Tool schemas: `/tools`
   - Discovery: `/.well-known/mcp.json`
   - Compatibility MCP: `/mcp` and `/mcp/` -> JSON-RPC `tools/list` / `tools/call` (auth required)
   - FastMCP native routes remain available through the mounted app.

## Extending
- Add tool/resource modules under `orbit_remote_mcp.tools`/`resources`, or point `ORBIT_MODULES` to external modules.
- Implement `list_tools`/`call_tool` or `list_resources`/`get_resource`.
- Provide valid resource URIs (e.g., `local://name`).
- Rebuild/restart; new handlers are auto-registered.
