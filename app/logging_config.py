import sys
import logging
import os
import re
from logging.handlers import RotatingFileHandler

from flask import request, has_request_context
from flask_login import current_user


LOG_FORMAT = "%(asctime)s | %(levelname)-5s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

EMAIL_RE = re.compile(r"([^@\s]{1,3})[^@\s]*(@[^\s]+)")
PHONE_RE = re.compile(r"(\+?\d{1,2})[\d\s\-\(\)]{5,}(\d{2})")


def mask_pii(text: str) -> str:
    if text is None:
        return ""
    text = str(text)
    text = EMAIL_RE.sub(lambda m: f"{m.group(1)}***{m.group(2)}", text)
    text = PHONE_RE.sub(lambda m: f"{m.group(1)}***{m.group(2)}", text)
    return text


class ContextFilter(logging.Filter):
    def filter(self, record):
        if has_request_context():
            try:
                if current_user.is_authenticated:
                    record.user = mask_pii(f"{current_user.email} ({current_user.role})")
                else:
                    record.user = "anonymous"
            except Exception:
                record.user = "anonymous"
            fwd = request.headers.get("X-Forwarded-For", "")
            record.ip = fwd.split(",")[0].strip() if fwd else (request.remote_addr or "?")
            record.method = request.method
            record.path = request.path
        else:
            record.user = "-"
            record.ip = "-"
            record.method = "-"
            record.path = "-"
        return True


class HumanFormatter(logging.Formatter):
    def format(self, record):
        record.message = mask_pii(record.getMessage())
        base = (
            f"{self.formatTime(record, DATE_FORMAT)} | {record.levelname:<5} "
            f"| user={record.user} | ip={record.ip} "
            f"| {record.method} {record.path} | {record.message}"
        )
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


def _make_handler(path, level):
    handler = RotatingFileHandler(
        path, maxBytes=5 * 1024 * 1024, backupCount=10, encoding="utf-8"
    )
    handler.setLevel(level)
    handler.setFormatter(HumanFormatter())
    handler.addFilter(ContextFilter())
    return handler


def configure_logging(app):
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    app_handler = _make_handler(os.path.join(log_dir, "app.log"), logging.INFO)
    err_handler = _make_handler(os.path.join(log_dir, "errors.log"), logging.WARNING)
    sec_handler = _make_handler(os.path.join(log_dir, "security.log"), logging.INFO)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(HumanFormatter())
    stream_handler.addFilter(ContextFilter())

    security_logger = logging.getLogger("vibe.security")
    security_logger.setLevel(logging.INFO)
    security_logger.propagate = False
    for h in list(security_logger.handlers):
        security_logger.removeHandler(h)
    security_logger.addHandler(sec_handler)

    action_logger = logging.getLogger("vibe.action")
    action_logger.setLevel(logging.INFO)
    action_logger.propagate = False
    for h in list(action_logger.handlers):
        action_logger.removeHandler(h)
    action_logger.addHandler(app_handler)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(app_handler)
    root.addHandler(err_handler)
    root.addHandler(stream_handler)

    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    app.logger.info("=== Vibe start ===")
    return app


def log_security(message):
    logging.getLogger("vibe.security").info(mask_pii(message))


def log_action(action, **kwargs):
    parts = [f"{k}={mask_pii(v)}" for k, v in kwargs.items()]
    text = action + (" — " + ", ".join(parts) if parts else "")
    logging.getLogger("vibe.action").info(text)