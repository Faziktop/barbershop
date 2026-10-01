"""Расширенные тесты безопасности: CSRF, доступ, IDOR, PII в логах."""
import os
import re


def test_csrf_token_present_on_login_page(client):
    r = client.get("/login")
    assert r.status_code == 200
    # На странице должна быть форма с csrf_token
    assert b"csrf_token" in r.data


def test_csrf_token_present_on_register_page(client):
    r = client.get("/register")
    assert r.status_code == 200
    assert b"csrf_token" in r.data


def test_sql_injection_in_login(client, db):
    """SQL-инъекция в поле логина не должна давать доступ."""
    r = client.post("/login", data={
        "login": "admin@test.local' OR '1'='1",
        "password": "anything",
    }, follow_redirects=True)
    assert r.status_code == 200
    # Не должно авторизовать — редирект на главную не произошёл,
    # значит фраза про неверный пароль
    assert b"\xd0\x9d\xd0\xb5\xd0\xb2\xd0\xb5\xd1\x80\xd0\xbd\xd1\x8b\xd0\xb9" in r.data or b"login" in r.data.lower()


def test_xss_in_salon_name_render(admin_client, db):
    """Создание салона с <script> — не должно выполняться."""
    r = admin_client.post("/admin/salons/new", data={
        "name": "<script>alert(1)</script>",
        "address": "addr",
        "phone": "",
        "description": "",
        "photo_url": "",
        "latitude": "",
        "longitude": "",
        "city_id": "",
    }, follow_redirects=True)
    assert r.status_code == 200
    # Скрипт должен быть экранирован
    assert b"<script>alert(1)</script>" not in r.data
    assert b"&lt;script&gt;" in r.data or b"alert(1)" in r.data


def test_user_cannot_cancel_other_booking(user_client, db):
    """IDOR: чужую запись отменить нельзя."""
    from app.models import Booking, User, Salon, Service, Specialist
    from datetime import datetime

    other_user = User(full_name="Other", email="other@test.local",
                      phone="+79008888888", role="client", phone_verified=True)
    other_user.set_password("pass123")
    db.session.add(other_user)
    db.session.commit()

    salon = Salon.query.first()
    service = Service.query.filter_by(salon_id=salon.id).first()
    specialist = Specialist.query.filter_by(salon_id=salon.id).first()

    foreign = Booking(
        user_id=other_user.id, salon_id=salon.id,
        service_id=service.id, specialist_id=specialist.id,
        booking_datetime=datetime(2032, 1, 1, 12, 0),
        status="pending",
    )
    db.session.add(foreign)
    db.session.commit()

    r = user_client.post(f"/bookings/{foreign.id}/cancel")
    assert r.status_code == 403
    # Запись не отменена
    assert Booking.query.get(foreign.id).status == "pending"


def test_client_cannot_delete_salon(user_client, db):
    from app.models import Salon
    salon = Salon.query.first()
    r = user_client.post(f"/admin/salons/{salon.id}/delete")
    assert r.status_code == 403
    assert Salon.query.get(salon.id) is not None


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    assert data["db"] is True


def test_pii_masked_in_logs(client, tmp_path):
    """Email и телефон в логах маскируются."""
    from app.logging_config import mask_pii

    assert mask_pii("admin@example.com") == "adm***@example.com"
    assert mask_pii("+79001234567") != "+79001234567"
    assert "***" in mask_pii("+79001234567")