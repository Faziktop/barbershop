"""Тесты безопасности: CSRF, права доступа, инъекции."""
import os
import pytest


def test_csrf_enabled(app):
    """Отдельно проверяем, что на боевой конфигурации CSRF включён."""
    # В app по умолчанию CSRFProtect, значит POST без токена должен падать.
    # Но в тестах мы отключили — поэтому создаём отдельное приложение.
    os.environ["SECRET_KEY"] = "test-csrf"
    from app import create_app
    a = create_app()
    a.config["WTF_CSRF_ENABLED"] = True
    a.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    client = a.test_client()
    r = client.post("/login", data={
        "login": "x@x.x", "password": "x",
    })
    # Должен быть 400 из-за отсутствия CSRF
    assert r.status_code == 400


def test_unauthenticated_profile_redirect(client):
    r = client.get("/profile")
    assert r.status_code in (302, 303)


def test_client_cannot_delete_salon(user_client, db):
    from app.models import Salon
    salon = Salon.query.first()
    r = user_client.post(f"/admin/salons/{salon.id}/delete")
    assert r.status_code == 403


def test_sql_injection_in_search(client, db):
    """Проверяем, что ORM защищает от инъекций."""
    r = client.get("/?q=' OR '1'='1")
    # Ошибки быть не должно, вернётся пустой список
    assert r.status_code == 200


def test_xss_in_salon_search(client, db):
    r = client.get("/?q=<script>alert(1)</script>")
    assert r.status_code == 200
    # В ответе скрипт должен быть экранирован
    assert b"<script>alert(1)</script>" not in r.data


def test_404_page(client):
    r = client.get("/no-such-page")
    assert r.status_code == 404


def test_api_find_city_invalid_params(client):
    r = client.get("/api/find-city?lat=abc&lon=xyz")
    assert r.status_code == 400


def test_api_find_city_valid(client, db):
    r = client.get("/api/find-city?lat=55.0&lon=37.0")
    assert r.status_code == 200
    data = r.get_json()
    assert "ok" in data