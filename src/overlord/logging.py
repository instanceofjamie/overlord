# SPDX-License-Identifier: Apache-2.0
import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for key in ("event_id", "session_id", "event_type", "status"):
            if hasattr(record, key):
                data[key] = str(getattr(record, key))
        return json.dumps(data)


def configure_logging(level: str) -> None:
    logger = logging.getLogger("overlord")
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False
