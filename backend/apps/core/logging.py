import hashlib
import json
import logging
import re

SENSITIVE_KEY_PATTERN = re.compile(
    r"(secret|answer|boundary|fantasy|safe_word|password|token|api_key|encryption_key)",
    re.IGNORECASE,
)


class SensitiveFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, dict):
            record.args = {
                key: ("[redacted]" if SENSITIVE_KEY_PATTERN.search(str(key)) else value)
                for key, value in record.args.items()
            }
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def anonymized_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
