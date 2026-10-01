"""Отправка алертов при 5xx. Работает без внешнего сервиса — просто пишет в лог.
Если задан ALERT_WEBHOOK_URL — шлёт POST через requests."""
import os
import logging
import threading

log = logging.getLogger(__name__)

WEBHOOK_URL = os.environ.get("ALERT_WEBHOOK_URL")


def send_alert(subject: str, body: str):
    """Алерт асинхронно, чтобы не тормозить ответ."""
    if not WEBHOOK_URL:
        log.warning(f"ALERT: {subject} | {body}")
        return
    t = threading.Thread(target=_post_webhook, args=(subject, body), daemon=True)
    t.start()


def _post_webhook(subject: str, body: str):
    try:
        import requests
        requests.post(
            WEBHOOK_URL,
            json={"text": f"*{subject}*\n{body}"},
            timeout=5,
        )
    except Exception as e:
        log.error(f"Не удалось отправить алерт: {e}")