"""Correlate requests without recording URLs, query strings, payloads or credentials."""

import json
import logging
import time
import uuid
from datetime import UTC, datetime

logger = logging.getLogger("pocketdesk.requests")


class SafeJSONFormatter(logging.Formatter):
    def format(self, record):
        fields = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }
        if record.name == "pocketdesk.requests":
            fields.update(
                {
                    key: getattr(record, key, None)
                    for key in ("request_id", "method", "status", "duration_ms")
                }
            )
            fields["event"] = "request_complete"
        else:
            # Third-party messages may include request paths or submitted values.
            fields["event"] = (
                "application_warning" if record.levelno < logging.ERROR else "application_error"
            )
            if record.exc_info:
                fields["exception_type"] = record.exc_info[0].__name__
        return json.dumps(fields, separators=(",", ":"))


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Generate our own ID: never echo an attacker-controlled header into logs.
        request.request_id = uuid.uuid4().hex
        started = time.monotonic()
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        logger.info(
            "request_complete",
            extra={
                "request_id": request.request_id,
                "method": request.method
                if request.method in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
                else "OTHER",
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
            },
        )
        return response
