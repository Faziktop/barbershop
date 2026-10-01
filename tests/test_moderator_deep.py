"""Deep-flow тесты модератора: свой салон, услуги, специалисты, статусы записей."""
from datetime import datetime

from app.models import (
    Salon, Service, Specialist, Booking, User, AuditLog,
)


def test_moderator_dashboard_shows_own_salon(mod_client, db):
    r = mod_client.get("/moderator/")
    assert r.status_code == 200
    assert b"Test Salon" in r.data


def test_moderator_can_full_crud_service(mod_client, db):
    salon = Salon.query.filter_by(name="Test Salon").first()

    # Create
    r = mod_client.post("/moderator/services/new", data={
        "name": "Mod Service",
        "description": "Desc",
        "price": "800",
        "duration_minutes": "30",
    }, follow_redirects=True)
    assert r.status_code == 200
    svc = Service.query.filter_by(name="Mod Service").first()
    assert svc is not None
    assert svc.salon_id == salon.id

    # Update
    r = mod_client.post(f"/moderator/services/{svc.id}/edit", data={
        "name": "Mod Service Updated",
        "description": "Desc2",
        "price": "900",
        "duration_minutes": "35",
        "is_active": "on",
    }, follow_redirects=True)
    assert r.status_code == 200
    assert Service.query.get(svc.id).name == "Mod Service Updated"

    # Delete
    r = mod_client.post(f"/moderator/services/{svc.id}/delete",
                        follow_redirects=True)
    assert r.status_code == 200
    assert Service.query.get(svc.id) is None


def test_moderator_can_full_crud_specialist(mod_client, db):
    salon = Salon.query.filter_by(name="Test Salon").first()

    r = mod_client.post("/moderator/specialists/new", data={
        "full_name": "Mod Master",
        "specialization": "Барбер",
        "description": "Desc",
        "photo_url": "",
    }, follow_redirects=True)
    assert r.status_code == 200
    sp = Specialist.query.filter_by(full_name="Mod Master").first()
    assert sp is not None

    r = mod_client.post(f"/moderator/specialists/{sp.id}/edit", data={
        "full_name": "Mod Master Updated",
        "specialization": "Топ",
        "description": "Desc",
        "photo_url": "",
        "is_active": "on",
    }, follow_redirects=True)
    assert r.status_code == 200
    assert Specialist.query.get(sp.id).full_name == "Mod Master Updated"

    r = mod_client.post(f"/moderator/specialists/{sp.id}/delete",
                        follow_redirects=True)
    assert r.status_code == 200
    assert Specialist.query.get(sp.id) is None


def test_moderator_can_change_booking_status(mod_client, db):
    salon = Salon.query.filter_by(name="Test Salon").first()
    service = Service.query.filter_by(salon_id=salon.id).first()
    specialist = Specialist.query.filter_by(salon_id=salon.id).first()
    client_user = User.query.filter_by(email="client@test.local").first()

    booking = Booking(
        user_id=client_user.id, salon_id=salon.id,
        service_id=service.id, specialist_id=specialist.id,
        booking_datetime=datetime(2031, 5, 5, 15, 0),
        status="pending",
    )
    db.session.add(booking)
    db.session.commit()

    # Подтвердить
    r = mod_client.post(f"/moderator/bookings/{booking.id}/status",
                        data={"status": "confirmed"},
                        follow_redirects=True)
    assert r.status_code == 200
    assert Booking.query.get(booking.id).status == "confirmed"

    # Завершить
    r = mod_client.post(f"/moderator/bookings/{booking.id}/status",
                        data={"status": "completed"},
                        follow_redirects=True)
    assert r.status_code == 200
    assert Booking.query.get(booking.id).status == "completed"

    entry = AuditLog.query.order_by(AuditLog.id.desc()).first()
    assert entry.action == "BOOKING STATUS"


def test_moderator_cannot_touch_other_salon_service(mod_client, db):
    """Модератор не может редактировать чужой салон."""
    # Создаём чужой салон и услугу в нём
    from app.models import City
    city = City.query.first()
    other = Salon(city_id=city.id, name="Other Salon", address="addr")
    db.session.add(other)
    db.session.flush()

    foreign_service = Service(salon_id=other.id, name="Foreign",
                              price=100, duration_minutes=30)
    db.session.add(foreign_service)
    db.session.commit()

    r = mod_client.get(f"/moderator/services/{foreign_service.id}/edit")
    # Должно быть 404: услуга не принадлежит салону модератора
    assert r.status_code == 404

    r = mod_client.post(f"/moderator/services/{foreign_service.id}/delete",
                        follow_redirects=False)
    assert r.status_code == 404
    # Услуга не удалена
    assert Service.query.get(foreign_service.id) is not None


def test_moderator_cannot_access_admin(mod_client):
    r = mod_client.get("/admin/")
    assert r.status_code == 403


def test_moderator_update_salon_info(mod_client, db):
    r = mod_client.post("/moderator/salon", data={
        "name": "Test Salon Mod",
        "address": "ул. Новая, д. 2",
        "phone": "+7 495 000-00-00",
        "description": "Moderator updated",
        "photo_url": "",
        "latitude": "55.1",
        "longitude": "37.1",
        "city_id": "",
    }, follow_redirects=True)
    assert r.status_code == 200
    salon = Salon.query.filter_by(name="Test Salon Mod").first()
    assert salon is not None

    entry = AuditLog.query.order_by(AuditLog.id.desc()).first()
    assert entry.action == "SALON UPDATED (moderator)"