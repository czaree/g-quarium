"""
logging helpers. every module does `log = get_logger(__name__)`, so no module hardcodes a name.
log lines show APP_NAME in place of the package name, e.g. `g-quarium.media.pipeline: ...`.
"""

import logging
import sys
from typing import TextIO

PACKAGE = "gquarium"
FORMAT = "%(asctime)s %(levelname)s %(display_name)s: %(message)s"

_HANDLER_FLAG = "_gquarium_handler"
_module_loggers: set[str] = set()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class AppNameFilter(logging.Filter):
    """
    sets record.display_name: the logger name with the package prefix swapped for app_name.
    """

    def __init__(self, app_name: str):
        super().__init__()
        self.app_name = app_name

    def filter(self, record: logging.LogRecord) -> bool:
        name = record.name
        if name == PACKAGE or name.startswith(PACKAGE + "."):
            name = self.app_name + name[len(PACKAGE):]
        record.display_name = name
        return True


def _level(name: str) -> int:
    level = logging.getLevelNamesMapping().get(name.strip().upper())
    if level is None:
        raise ValueError(f"unknown log level {name!r}")
    return level


def parse_log_levels(spec: str) -> dict[str, int]:
    """
    'media.pipeline=debug,web=info' -> {'media.pipeline': 10, 'web': 20}. blank -> {}.
    """
    levels: dict[str, int] = {}
    for item in filter(None, (part.strip() for part in spec.split(","))):
        module, sep, level = item.partition("=")
        if not sep or not module.strip():
            raise ValueError(f"bad LOG_LEVELS entry {item!r} (expected module=level)")
        levels[module.strip()] = _level(level)
    return levels


def configure_logging(app_name: str, level: str = "info", levels: str = "",
                      stream: TextIO | None = None) -> None:
    """
    install one stderr handler on the root logger. safe to call more than once.
    """
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, _HANDLER_FLAG, False):
            root.removeHandler(handler)
    handler = logging.StreamHandler(stream or sys.stderr)
    setattr(handler, _HANDLER_FLAG, True)
    handler.setFormatter(logging.Formatter(FORMAT))
    handler.addFilter(AppNameFilter(app_name))
    root.addHandler(handler)
    root.setLevel(_level(level))

    for name in _module_loggers:
        logging.getLogger(name).setLevel(logging.NOTSET)
    _module_loggers.clear()
    for module, module_level in parse_log_levels(levels).items():
        name = f"{PACKAGE}.{module}"
        logging.getLogger(name).setLevel(module_level)
        _module_loggers.add(name)
