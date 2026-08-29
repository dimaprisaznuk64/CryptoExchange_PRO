import json
import logging
from datetime import datetime, UTC

audit_logger = logging.getLogger("audit")

MAX_FIELD_LENGTH = 256


def _safe(value) -> str:
    text = str(value)
    if len(text) > MAX_FIELD_LENGTH:
        text = text[:MAX_FIELD_LENGTH] + "..."
    return text


def log(event: str, **fields) -> None:
    """Emit a structured JSON audit record (no secrets, truncated values)."""
    record = {"event": event, "at": datetime.now(UTC).isoformat()}
    record.update({k: _safe(v) for k, v in fields.items()})
    audit_logger.info(json.dumps(record, ensure_ascii=False))