# Contributing to OrbitRemoteMCP

Thanks for considering a contribution! This project is a lightweight MCP framework; please keep changes focused, documented, and tested.

## Getting started
- Fork and clone the repo.
- Install deps: `pip install -e .[dev]` (or use Docker/uv).
- Copy `.env.example` to `.env` and set `ORBIT_AUTH_KEY` (and `OPENWEATHER_API_KEY` only if you keep the sample).

## Development workflow
- Run locally: `python -m orbit_remote_mcp --host 0.0.0.0 --port 8000 --transport streamable-http`
- Docker: `docker compose up --build`
- Tests: `pytest`
- Linting: run `ruff` if available (config is in `pyproject.toml`).

## Code style and scope
- Keep the framework generic; samples are optional and should remain simple.
- Prefer async/await, small modules, and clear docstrings/comments where needed.
- Avoid introducing new dependencies unless necessary.
- For new tools/resources, ensure they implement `list_tools`/`call_tool` or `list_resources`/`get_resource`, and provide valid resource URIs.

## PR guidelines
- Describe the change and its motivation.
- Include tests or explain why they’re not needed.
- Update docs/README where behavior or configuration changes.
- Keep commits focused; rebase/cleanup noisy histories before opening the PR.

## Reporting issues
- Include environment info (OS, Python version, how you ran it: local vs Docker).
- Steps to reproduce, expected vs actual results, and logs if available.

## License
By contributing, you agree that your contributions will be licensed under the MIT License.
