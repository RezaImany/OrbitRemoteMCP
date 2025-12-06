# OrbitRemoteMCP

HTTP-only, streamable MCP framework with secure auth, rate limiting, session tokens, and a drop-in plugin model. Includes optional sample code (OpenWeather tool, simple resource) purely as reference—you can remove or replace them freely.

## Highlights
- Streamable HTTP transport (no stdio), ready for remote deployment.
- Auth: API key + signed session tokens, CORS, body-size and rate limits.
- Auto-discovers built-in tools/resources; optional entrypoints or `ORBIT_MODULES` for plugins.
- Compatibility `/mcp` endpoint for JSON-RPC over HTTP (no special Accept header required).
- Minimal dependencies (FastAPI/Starlette core, Pydantic v2, httpx async client).

## Quick start (local)
Copy the sample env and fill in your values (the real `.env` stays untracked):
```bash
cp .env.example .env
pip install -e .
python -m orbit_remote_mcp --host 0.0.0.0 --port 8000 --transport streamable-http
```

## Quick start (Docker)
Copy `.env.example` to `.env`, set the values you need, then start:
```bash
cd orbitRemoteMCP
docker compose up --build
```
Container exposes `8000` by default.

## Configuration
Only set what you need; sane defaults are included.

| Variable | Default | Purpose |
| --- | --- | --- |
| ORBIT_HOST | 0.0.0.0 | Bind host |
| ORBIT_PORT | 8000 | Bind port |
| ORBIT_REQUIRE_AUTH | true | Enforce auth |
| ORBIT_AUTH_KEY | (none; required) | API key and token signing secret |
| LOG_LEVEL | INFO | Logging level |
| OPENWEATHER_API_KEY | (none) | Only needed if you keep/use the OpenWeather sample |
| ORBIT_ALLOWED_ORIGINS | * | CORS allowlist |
| ORBIT_RATE_LIMIT | 60 | Requests per minute per client |
| ORBIT_MAX_BODY_BYTES | 1048576 | Max request body size |
| ORBIT_SESSION_TTL_SECONDS | 1800 | Session token lifetime |
| ORBIT_MODULES | (auto) | Custom plugin modules (comma-separated) |

## Endpoints
- `GET /diagnostics/healthcheck` – liveness
- `GET /diagnostics/ready` – readiness
- `POST /sessions` – returns `{ session_token, expires_in }` (auth required)
- `GET /tools` – tool schemas (auth required)
- `GET /.well-known/mcp.json` – discovery info
- `POST /mcp` – JSON-RPC (compat) for `tools/list` and `tools/call` (auth required)

## Calling tools (curl)
Use the compatibility `/mcp` endpoint with standard JSON-RPC payloads.
```bash
# list tools
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer change-me" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# call current_weather
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer change-me" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"current_weather","arguments":{"city":"Paris","country":"FR","units":"metric"}}}'
```

## Use as a framework (bring your own tools/resources)
1. Optional: remove the samples by deleting `src/orbit_remote_mcp/tools/openweather.py` and `src/orbit_remote_mcp/resources/sample.py` if you don’t want them discovered.
2. Create your tool module under `orbit_remote_mcp/tools` with a class that implements:
   ```python
   from mcp.types import Tool, TextContent

   class MyTools:
       async def list_tools(self) -> list[Tool]:
           return [
               Tool(
                   name="hello",
                   description="Say hello",
                   inputSchema={"type": "object", "properties": {"name": {"type": "string"}}},
               ),
           ]

       async def call_tool(self, name: str, arguments: dict[str, object]):
           if name != "hello":
               raise ValueError("Unknown tool")
           who = arguments.get("name", "world")
           return [TextContent(type="text", text=f"Hello, {who}!")]
   ```
3. Add resources similarly under `orbit_remote_mcp/resources` with `list_resources`/`get_resource` (provide a valid `uri`, e.g., `local://something`).
4. If your modules live elsewhere, set `ORBIT_MODULES=your.module.path` (comma-separated for many); built-ins are auto-loaded when not set.
5. Rebuild/restart. Your tools will appear in `/tools` and `/mcp`.

## Samples (optional)
- **OpenWeather tool**: `current_weather` (params: `city` required, `country` optional, `units` `metric`|`imperial` default `metric`; needs `OPENWEATHER_API_KEY`).
- **Sample resource**: static status resource at `local://status`.

## Plugin development
1) Add a module under `orbit_remote_mcp.tools` or `orbit_remote_mcp.resources` implementing `list_tools`/`call_tool` or `list_resources`/`get_resource`.
2) Auto-discovery loads built-ins by default. For external modules, set `ORBIT_MODULES=your.module.path`.
3) Rebuild/restart; tools will be listed via `/tools` and `/mcp`. Remove the sample modules if you don’t need them.

## Security notes
- Keep `ORBIT_REQUIRE_AUTH=true` and set a strong `ORBIT_AUTH_KEY`.
- Use session tokens from `/sessions` to avoid sending the API key on every request.
- Tune `ORBIT_RATE_LIMIT`, `ORBIT_MAX_BODY_BYTES`, and `ORBIT_ALLOWED_ORIGINS` for your deployment.

## Testing
```bash
pip install -e .[dev]
pytest
```

## Architecture
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a component overview and request flow.

## Contributing
PRs welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before sending changes.

## License
MIT. See [LICENSE](LICENSE).
