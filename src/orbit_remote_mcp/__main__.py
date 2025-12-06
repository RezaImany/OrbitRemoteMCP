"""OrbitRemoteMCP entrypoint."""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from .config import Settings
from .core.server import build_server
from .http.app import build_app
from .logging import configure_logging, get_logger

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OrbitRemoteMCP server")
    parser.add_argument("--host", default=None, help="Host to bind")
    parser.add_argument("--port", type=int, default=None, help="Port to bind")
    parser.add_argument(
        "--transport",
        choices=["streamable-http"],
        default="streamable-http",
        help="Transport type (streamable-http only)",
    )
    parser.add_argument("--log-level", default=None, help="Log level (INFO, DEBUG, etc)")
    parser.add_argument(
        "--log-json",
        dest="log_json",
        action="store_const",
        const=True,
        default=None,
        help="Enable JSON logs",
    )
    parser.add_argument("--name", default=None, help="Server name override")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    settings = Settings.from_cli(
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        log_json=args.log_json,
        server_name=args.name,
    )

    configure_logging(settings.log_level, settings.log_json)
    logger.info("Starting OrbitRemoteMCP on %s:%s", settings.host, settings.port)

    server, tool_schemas = build_server(settings)
    app = build_app(server, settings, tool_schemas)

    import uvicorn

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
