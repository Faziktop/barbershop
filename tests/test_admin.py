"""Тесты админ-панели и прав доступа."""
from app.models import Salon


def test_admin_dashboard_requires_login(client):
    r = client.get("/admin/")
    assert r.status_code in (302, 303)


def test_admin_dashboard_denied_for_client(user_client):
    r = user_client.get("/admin/")
    assert r.status_code == 403


def test_admin_dashboard_allowed(admin_client):
    r = admin_client.get("/admin/")
    assert r.status_code == 200


def test_admin_can_list_salons(admin_client):
    r = admin_client.get("/admin/salons")
    assert r.status_code == 200


def test_admin_can_edit_salon(admin_client, db):
    salon = Salon.query.first()
    r = admin_client.get(f"/admin/salons/{salon.id}/edit")
    assert r.status_code == 200


def test_admin_can_create_salon(admin_client, db):
    r = admin_client.post("/admin/salons/new", data={
        "name": "Новый салон",
        "address": "ул. Новая, д. 1",
        "phone": "+7 000 000-00-00",
        "description": "Тест",
        "photo_url": "",
        "latitude": "55.0",
        "longitude": "37.0",
        "city_id": "",
    }, follow_redirects=True)
    assert r.status_code == 200
    assert Salon.query.filter_by(name="Новый салон").first() is not None


def test_admin_can_create_service(admin_client, db):
    salon = Salon.query.first()
    r = admin_client.post(f"/admin/salons/{salon.id}/services/new", data={
        "name": "Новая услуга",
        "description": "Описание",
        "price": "500",
        "duration_minutes": "30",
    }, follow_redirects=True)
    assert r.status_code == 200


def test_admin_users_page(admin_client):
    r = admin_client.get("/admin/users")
    assert r.status_code == 200
    assert b"admin@test.local" in r.data