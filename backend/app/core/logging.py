import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from app.core.config import get_settings

settings = get_settings()

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    formatter = logging.Formatter(LOG_FORMAT)

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    root.addHandler(stream)

    os.makedirs("logs", exist_ok=True)

    file_handler = RotatingFileHandler(
        "logs/app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    audit = logging.getLogger("audit")
    audit.setLevel(logging.INFO)
    audit.propagate = False
    audit_handler = RotatingFileHandler(
        "logs/audit.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    audit_handler.setFormatter(logging.Formatter("%(message)s"))
    audit.addHandler(audit_handler)
