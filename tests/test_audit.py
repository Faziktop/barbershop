"""Тесты журнала аудита: запись событий, фильтрация, доступ."""
from app.models import AuditLog, User


def test_audit_view_requires_admin(client):
    """Клиент не может открыть /admin/audit."""
    r = client.get("/admin/audit")
    assert r.status_code in (302, 303)  # редирект на логин


def test_audit_view_denied_for_client(user_client):
    r = user_client.get("/admin/audit")
    assert r.status_code == 403


def test_audit_view_allowed_for_admin(admin_client):
    r = admin_client.get("/admin/audit")
    assert r.status_code == 200


def test_user_login_creates_audit_entry(admin_client, db):
    """Логин через POST /login создаёт запись в audit_log."""
    entry = AuditLog.query.filter_by(action="USER LOGIN")\
                          .order_by(AuditLog.id.desc()).first()
    assert entry is not None
    assert entry.user_email == "admin@test.local"
    assert entry.role == "admin"


def test_audit_search_by_action(admin_client, db):
    # Создадим салон, чтобы точно появилась запись
    admin_client.post("/admin/salons/new", data={
        "name": "Search Salon",
        "address": "addr",
        "phone": "",
        "description": "",
        "photo_url": "",
        "latitude": "",
        "longitude": "",
        "city_id": "",
    }, follow_redirects=True)

    r = admin_client.get("/admin/audit?q=SALON CREATED")
    assert r.status_code == 200
    assert b"SALON CREATED" in r.data


def test_audit_contains_ip(admin_client, db):
    entry = AuditLog.query.order_by(AuditLog.id.desc()).first()
    assert entry is not None
    # IP должен быть (127.0.0.1 или из X-Forwarded-For)
    assert entry.ip is not None
    assert len(entry.ip) > 0


def test_audit_records_target_id(admin_client, db):
    admin_client.post("/admin/salons/new", data={
        "name": "Target Salon",
        "address": "addr",
        "phone": "",
        "description": "",
        "photo_url": "",
        "latitude": "",
        "longitude": "",
        "city_id": "",
    }, follow_redirects=True)

    from app.models import Salon
    salon = Salon.query.filter_by(name="Target Salon").first()
    entry = AuditLog.query.filter_by(action="SALON CREATED")\
                          .order_by(AuditLog.id.desc()).first()
    assert entry.target_id == salon.id