"""Тесты кабинета модератора."""
from app.models import Salon, Service


def test_moderator_dashboard_requires_login(client):
    r = client.get("/moderator/")
    assert r.status_code in (302, 303)


def test_moderator_dashboard_denied_for_client(user_client):
    r = user_client.get("/moderator/")
    assert r.status_code == 403


def test_moderator_dashboard_allowed(mod_client):
    r = mod_client.get("/moderator/")
    assert r.status_code == 200


def test_moderator_can_view_bookings(mod_client):
    r = mod_client.get("/moderator/bookings")
    assert r.status_code == 200


def test_moderator_can_add_service(mod_client, db):
    salon = Salon.query.first()
    r = mod_client.post("/moderator/services/new", data={
        "name": "Услуга модератора",
        "description": "Desc",
        "price": "700",
        "duration_minutes": "45",
    }, follow_redirects=True)
    assert r.status_code == 200
    assert Service.query.filter_by(name="Услуга модератора").first() is not None


def test_moderator_cannot_access_admin(mod_client):
    r = mod_client.get("/admin/")
    # Модератор не админ, но у нас админ имеет все права модератора,
    # а модератор — только свой салон. Ожидаем 403.
    assert r.status_code == 403