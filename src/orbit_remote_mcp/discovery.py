"""Plugin discovery utilities."""

from __future__ import annotations

import importlib
import inspect
import logging
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Callable, Iterable, List, Sequence
import pkgutil

from .protocols import is_resource_handler, is_tool_handler

logger = logging.getLogger(__name__)


def _collect_entrypoint_modules(group: str = "orbit_remote_mcp.plugins") -> list[str]:
    try:
        eps = entry_points()
        selected = eps.select(group=group) if hasattr(eps, "select") else eps.get(group, [])
    except Exception:
        return []
    return [ep.value for ep in selected]


def _auto_modules() -> list[str]:
    """Auto-discover all modules under built-in tools/resources packages."""
    discovered: list[str] = []
    for base_pkg in ("orbit_remote_mcp.tools", "orbit_remote_mcp.resources"):
        try:
            pkg = importlib.import_module(base_pkg)
        except Exception:
            continue
        pkg_paths: list[Path] = []
        # Namespace packages expose __path__, regular packages expose __file__
        if hasattr(pkg, "__path__"):
            pkg_paths.extend([Path(p) for p in pkg.__path__])  # type: ignore[arg-type]
        elif getattr(pkg, "__file__", None):
            pkg_paths.append(Path(pkg.__file__).parent)  # type: ignore[arg-type]
        else:
            continue

        for pkg_path in pkg_paths:
            for _, name, ispkg in pkgutil.iter_modules([str(pkg_path)]):
                if name.startswith("_"):
                    continue
                discovered.append(f"{base_pkg}.{name}")
    return discovered


def _unique(seq: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def discover_handlers(
    modules: Sequence[str],
    predicate: Callable[[object], bool],
) -> list[Any]:
    handlers: list[Any] = []
    for module_name in modules:
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            logger.warning("Failed to import module %s: %s", module_name, exc)
            continue

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != module_name:
                continue
            try:
                instance = obj()
            except Exception as exc:
                logger.warning("Failed to instantiate %s.%s: %s", module_name, obj.__name__, exc)
                continue

            if predicate(instance):
                handlers.append(instance)
    return handlers


def discover_tool_handlers(configured_modules: Sequence[str]) -> list[Any]:
    modules = configured_modules or _auto_modules()
    modules = _unique([*modules, *_collect_entrypoint_modules()])
    return discover_handlers(modules, is_tool_handler)


def discover_resource_handlers(configured_modules: Sequence[str]) -> list[Any]:
    modules = configured_modules or _auto_modules()
    modules = _unique([*modules, *_collect_entrypoint_modules()])
    return discover_handlers(modules, is_resource_handler)
