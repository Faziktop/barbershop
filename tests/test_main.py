"""Тесты главной страницы, салонов, записей."""
from app.models import Salon


def test_index_opens(client, db):
    r = client.get("/")
    assert r.status_code == 200
    assert "Vibe".encode() in r.data


def test_index_shows_salon(client, db):
    r = client.get("/")
    assert b"Test Salon" in r.data


def test_salon_detail(client, db):
    salon = Salon.query.first()
    r = client.get(f"/salon/{salon.id}")
    assert r.status_code == 200
    assert b"Test Salon" in r.data


def test_salon_not_found(client):
    r = client.get("/salon/99999")
    assert r.status_code == 404


def test_booking_requires_login(client, db):
    salon = Salon.query.first()
    r = client.get(f"/salon/{salon.id}/book")
    # Без логина — редирект на /login
    assert r.status_code in (302, 303)
    assert "/login" in r.headers.get("Location", "")


def test_profile_requires_login(client):
    r = client.get("/profile")
    assert r.status_code in (302, 303)


def test_api_cities(client, db):
    r = client.get("/api/cities?q=Тест")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list)
    assert any("Тест" in c["name"] for c in data)


def test_api_cities_empty_query(client, db):
    r = client.get("/api/cities")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_rules_page(client):
    r = client.get("/rules")
    assert r.status_code == 200


def test_contacts_page(client):
    r = client.get("/contacts")
    assert r.status_code == 200