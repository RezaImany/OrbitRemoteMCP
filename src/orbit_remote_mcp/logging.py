"""Logging helpers for OrbitRemoteMCP."""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from typing import Any, Dict

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def _json_formatter(record: logging.LogRecord) -> str:
    payload: Dict[str, Any] = {
        "level": record.levelname,
        "logger": record.name,
        "msg": record.getMessage(),
    }
    if record.exc_info:
        payload["exc_info"] = logging.formatException(record.exc_info)
    req_id = request_id_var.get()
    if req_id:
        payload["request_id"] = req_id
    return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str = "INFO", json_logs: bool = False) -> None:
    logging.captureWarnings(True)
    log_level = getattr(logging, level.upper(), logging.INFO)
    handlers: list[logging.Handler] = []

    if json_logs:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(fmt="%(message)s"))
        handler.emit = lambda record: logging.StreamHandler.emit(handler, record)
        handler.format = lambda record: _json_formatter(record)
        handlers.append(handler)
    else:
        formatter = logging.Formatter(
            fmt="[%(asctime)s] %(levelname)s %(name)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handlers.append(handler)

    logging.basicConfig(level=log_level, handlers=handlers, force=True)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def set_request_id(request_id: str | None) -> None:
    request_id_var.set(request_id)

