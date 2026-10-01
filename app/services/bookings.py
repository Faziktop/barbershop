"""Бизнес-логика бронирований."""
from datetime import datetime, timedelta, date

from sqlalchemy.exc import IntegrityError

from .. import db
from ..models import Booking, Service, Specialist, STATUS_PENDING


WORK_START_HOUR = 9
WORK_END_HOUR = 20
SLOT_STEP_MINUTES = 30


def generate_slots_for_date(day: date):
    slots = []
    current = datetime.combine(day, datetime.min.time()).replace(hour=WORK_START_HOUR)
    end = datetime.combine(day, datetime.min.time()).replace(hour=WORK_END_HOUR)
    while current < end:
        slots.append(current)
        current += timedelta(minutes=SLOT_STEP_MINUTES)
    return slots


def get_available_slots(specialist_id: int, day: date):
    all_slots = generate_slots_for_date(day)
    taken = {
        b.booking_datetime
        for b in Booking.query.filter_by(specialist_id=specialist_id)
        .filter(Booking.status.in_(["pending", "confirmed"]))
        .all()
    }
    now = datetime.now()
    return [s for s in all_slots if s not in taken and s > now]


class BookingError(Exception):
    pass


def create_booking(user_id: int, salon_id: int, service_id: int,
                   specialist_id: int, slot_str: str, note: str):
    """Создаёт бронь. Бросает BookingError с понятным текстом."""
    service = Service.query.filter_by(id=service_id, salon_id=salon_id).first()
    specialist = Specialist.query.filter_by(id=specialist_id, salon_id=salon_id).first()

    if not service or not specialist:
        raise BookingError("Выберите услугу и специалиста.")
    if not slot_str:
        raise BookingError("Выберите время.")

    try:
        booking_dt = datetime.strptime(slot_str, "%Y-%m-%dT%H:%M")
    except ValueError:
        raise BookingError("Некорректное время.")

    if booking_dt < datetime.now():
        raise BookingError("Нельзя на прошедшее время.")

    clash = Booking.query.filter_by(
        specialist_id=specialist.id, booking_datetime=booking_dt
    ).filter(Booking.status.in_(["pending", "confirmed"])).first()
    if clash:
        raise BookingError("Это время занято.")

    booking = Booking(
        user_id=user_id, salon_id=salon_id, service_id=service.id,
        specialist_id=specialist.id, booking_datetime=booking_dt,
        status=STATUS_PENDING, note=note,
    )
    db.session.add(booking)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise BookingError("Это время только что заняли. Попробуйте другое.")

    return booking