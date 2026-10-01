"""
Настройка логирования. Пишем в logs/ с ротацией по 5 МБ, храним 10 файлов.

Форматы:
  logs/app.log       — все INFO и выше
  logs/errors.log    — только WARNING и выше (ошибки, исключения)
  logs/security.log  — события безопасности (логины, баны, CSRF)
"""
import logging
import os
from logging.handlers import RotatingFileHandler

from flask import request, has_request_context
from flask_login import current_user


LOG_FORMAT = "%(asctime)s | %(levelname)-5s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class ContextFilter(logging.Filter):
    """Добавляет в каждую запись пользователя, IP и запрос, если они есть."""

    def filter(self, record):
        if has_request_context():
            # Пользователь
            try:
                if current_user.is_authenticated:
                    record.user = f"{current_user.email} ({current_user.role})"
                else:
                    record.user = "anonymous"
            except Exception:
                record.user = "anonymous"

            # IP (учитываем X-Forwarded-For за прокси)
            fwd = request.headers.get("X-Forwarded-For", "")
            record.ip = fwd.split(",")[0].strip() if fwd else (request.remote_addr or "?")

            # Метод и путь
            record.method = request.method
            record.path = request.path
        else:
            record.user = "-"
            record.ip = "-"
            record.method = "-"
            record.path = "-"

        return True


class HumanFormatter(logging.Formatter):
    """Читаемый формат: время | уровень | user | ip | METHOD PATH | сообщение."""

    def format(self, record):
        record.message = record.getMessage()
        base = f"{self.formatTime(record, DATE_FORMAT)} | {record.levelname:<5} " \
               f"| user={record.user} | ip={record.ip} " \
               f"| {record.method} {record.path} | {record.message}"
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

    # Отдельный логгер для безопасности, чтобы писать только туда события безопасности
    security_logger = logging.getLogger("vibe.security")
    security_logger.setLevel(logging.INFO)
    security_logger.propagate = False
    if not security_logger.handlers:
        security_logger.addHandler(sec_handler)

    # Основной логгер приложения
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Убираем дефолтные обработчики, чтобы не дублировать в консоль
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(app_handler)
    root.addHandler(err_handler)

    # Чтобы Werkzeug тоже писал в app.log, но не спамил access-логами
    werk = logging.getLogger("werkzeug")
    werk.setLevel(logging.WARNING)

    # Чтобы SQLAlchemy не спамил
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    app.logger.info("=== Vibe start ===")
    return app


def log_security(message):
    """Логировать событие безопасности."""
    logging.getLogger("vibe.security").info(message)


def log_action(action, **kwargs):
    """Логировать действие пользователя. Пример:
       log_action('Salon updated', salon_id=8, name='Vibe на Тверской')
    """
    parts = [f"{k}={v}" for k, v in kwargs.items()]
    text = action + (" — " + ", ".join(parts) if parts else "")
    logging.getLogger("vibe.action").info(text)