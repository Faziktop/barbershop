"""Deep-flow тест бронирования: клиент создаёт, модератор подтверждает."""
from datetime import date, timedelta

from app.models import (
    Salon, Service, Specialist, Booking, AuditLog,
)


def _booking_url(salon_id):
    return f"/salon/{salon_id}/book"


def test_client_creates_booking(user_client, db):
    salon = Salon.query.filter_by(name="Test Salon").first()
    service = Service.query.filter_by(salon_id=salon.id).first()
    specialist = Specialist.query.filter_by(salon_id=salon.id).first()

    # Дата: завтра, чтобы не попасть в «нельзя на прошедшее»
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    slot = f"{tomorrow}T12:00"

    r = user_client.post(_booking_url(salon.id), data={
        "service_id": str(service.id),
        "specialist_id": str(specialist.id),
        "slot": slot,
        "note": "Тестовое бронирование",
    }, follow_redirects=True)
    assert r.status_code == 200

    booking = Booking.query.filter_by(note="Тестовое бронирование").first()
    assert booking is not None
    assert booking.status == "pending"
    assert booking.specialist_id == specialist.id

    entry = AuditLog.query.filter_by(action="BOOKING CREATED")\
                          .order_by(AuditLog.id.desc()).first()
    assert entry is not None
    assert entry.target_id == booking.id


def test_double_booking_same_slot_rejected(user_client, db):
    """Попытка занять тот же слот повторно — отказ."""
    salon = Salon.query.filter_by(name="Test Salon").first()
    service = Service.query.filter_by(salon_id=salon.id).first()
    specialist = Specialist.query.filter_by(salon_id=salon.id).first()

    tomorrow = (date.today() + timedelta(days=2)).isoformat()
    slot = f"{tomorrow}T15:00"

    # Первая запись
    r1 = user_client.post(_booking_url(salon.id), data={
        "service_id": str(service.id),
        "specialist_id": str(specialist.id),
        "slot": slot,
        "note": "Первая",
    }, follow_redirects=True)
    assert r1.status_code == 200
    assert Booking.query.filter_by(note="Первая").first() is not None

    # Вторая на тот же слот — должна провалиться (BookingError)
    r2 = user_client.post(_booking_url(salon.id), data={
        "service_id": str(service.id),
        "specialist_id": str(specialist.id),
        "slot": slot,
        "note": "Вторая",
    }, follow_redirects=True)
    assert r2.status_code == 200
    assert Booking.query.filter_by(note="Вторая").first() is None


def test_booking_for_past_date_rejected(user_client, db):
    salon = Salon.query.filter_by(name="Test Salon").first()
    service = Service.query.filter_by(salon_id=salon.id).first()
    specialist = Specialist.query.filter_by(salon_id=salon.id).first()

    past = "2020-01-01T12:00"
    r = user_client.post(_booking_url(salon.id), data={
        "service_id": str(service.id),
        "specialist_id": str(specialist.id),
        "slot": past,
        "note": "Прошлое",
    }, follow_redirects=True)
    assert r.status_code == 200
    assert Booking.query.filter_by(note="Прошлое").first() is None


def test_client_cancel_booking(user_client, db):
    """Клиент может отменить свою запись."""
    salon = Salon.query.filter_by(name="Test Salon").first()
    service = Service.query.filter_by(salon_id=salon.id).first()
    specialist = Specialist.query.filter_by(salon_id=salon.id).first()

    tomorrow = (date.today() + timedelta(days=3)).isoformat()
    slot = f"{tomorrow}T10:00"

    user_client.post(_booking_url(salon.id), data={
        "service_id": str(service.id),
        "specialist_id": str(specialist.id),
        "slot": slot,
        "note": "На отмену",
    }, follow_redirects=True)

    booking = Booking.query.filter_by(note="На отмену").first()
    assert booking is not None

    r = user_client.post(f"/bookings/{booking.id}/cancel",
                         follow_redirects=True)
    assert r.status_code == 200
    assert Booking.query.get(booking.id).status == "cancelled"

    entry = AuditLog.query.filter_by(action="BOOKING CANCELLED")\
                          .order_by(AuditLog.id.desc()).first()
    assert entry is not None
    assert entry.target_id == booking.id