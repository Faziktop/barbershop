"""Запись аудита юридически значимых действий в БД."""
from flask import request
from flask_login import current_user

from . import db
from .models import AuditLog


def audit(action: str, target_type: str = None, target_id: int = None,
          details: str = None, commit: bool = True):
    """Пишет событие в audit_log. Никогда не падает."""
    try:
        user_id = None
        user_email = None
        role = None
        if current_user and current_user.is_authenticated:
            user_id = current_user.id
            user_email = current_user.email
            role = current_user.role

        ip = None
        if request:
            fwd = request.headers.get("X-Forwarded-For", "")
            if fwd:
                ip = fwd.split(",")[0].strip()
            else:
                ip = request.remote_addr

        entry = AuditLog(
            user_id=user_id,
            user_email=user_email,
            role=role,
            ip=ip,
            action=(action or "")[:200],
            target_type=(target_type or "")[:50] or None,
            target_id=target_id,
            details=(details or "")[:1000] or None,
        )
        db.session.add(entry)
        if commit:
            db.session.commit()
    except Exception:
        db.session.rollback()