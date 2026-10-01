from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort,
)
from flask_login import login_required, current_user

from . import db
from .models import Service, Specialist, Booking, Salon, Region, SalonPhoto, ROLE_MODERATOR
from .decorators import roles_required
from .audit import audit
from .media import save_salon_photo, delete_salon_photo_file

moderator_bp = Blueprint("moderator", __name__)


def _current_salon():
    if not current_user.salon_id:
        abort(403, "У вас не назначен салон. Обратитесь к администратору.")
    return Salon.query.get_or_404(current_user.salon_id)


@moderator_bp.before_request
@login_required
@roles_required(ROLE_MODERATOR)
def guard():
    pass


@moderator_bp.route("/")
def dashboard():
    salon = _current_salon()
    pending_count = Booking.query.filter_by(salon_id=salon.id, status="pending").count()
    services_count = Service.query.filter_by(salon_id=salon.id).count()
    specialists_count = Specialist.query.filter_by(salon_id=salon.id).count()
    return render_template(
        "moderator/dashboard.html",
        salon=salon,
        pending_count=pending_count,
        services_count=services_count,
        specialists_count=specialists_count,
    )


# ---------- Services ----------

@moderator_bp.route("/services")
def services():
    salon = _current_salon()
    items = Service.query.filter_by(salon_id=salon.id).order_by(Service.name).all()
    return render_template("moderator/services.html", salon=salon, services=items)


@moderator_bp.route("/services/new", methods=["GET", "POST"])
def service_new():
    salon = _current_salon()
    if request.method == "POST":
        name = request.form.get("name", "").strip()[:150]
        description = request.form.get("description", "").strip()[:2000]
        price = request.form.get("price", type=float) or 0
        duration = request.form.get("duration_minutes", type=int) or 30
        if not name:
            flash("Укажите название.", "danger")
        elif price < 0 or price > 1_000_000:
            flash("Некорректная цена.", "danger")
        elif duration < 5 or duration > 24 * 60:
            flash("Некорректная длительность.", "danger")
        else:
            db.session.add(Service(salon_id=salon.id, name=name, description=description,
                                   price=price, duration_minutes=duration))
            db.session.commit()
            audit("SERVICE CREATED", target_type="salon", target_id=salon.id,
                  details=f"name={name}")
            flash("Услуга добавлена.", "success")
            return redirect(url_for("moderator.services"))
    return render_template("moderator/service_form.html", salon=salon, service=None)


@moderator_bp.route("/services/<int:service_id>/edit", methods=["GET", "POST"])
def service_edit(service_id):
    salon = _current_salon()
    service = Service.query.filter_by(id=service_id, salon_id=salon.id).first_or_404()
    if request.method == "POST":
        service.name = request.form.get("name", "").strip()[:150]
        service.description = request.form.get("description", "").strip()[:2000]
        price = request.form.get("price", type=float) or 0
        duration = request.form.get("duration_minutes", type=int) or 30
        if price < 0 or price > 1_000_000:
            flash("Некорректная цена.", "danger")
            return render_template("moderator/service_form.html", salon=salon, service=service)
        if duration < 5 or duration > 24 * 60:
            flash("Некорректная длительность.", "danger")
            return render_template("moderator/service_form.html", salon=salon, service=service)
        service.price = price
        service.duration_minutes = duration
        service.is_active = bool(request.form.get("is_active"))
        db.session.commit()
        audit("SERVICE UPDATED", target_type="service", target_id=service.id)
        flash("Услуга обновлена.", "success")
        return redirect(url_for("moderator.services"))
    return render_template("moderator/service_form.html", salon=salon, service=service)


@moderator_bp.route("/services/<int:service_id>/delete", methods=["POST"])
def service_delete(service_id):
    salon = _current_salon()
    service = Service.query.filter_by(id=service_id, salon_id=salon.id).first_or_404()
    db.session.delete(service)
    db.session.commit()
    audit("SERVICE DELETED", target_type="service", target_id=service_id)
    flash("Услуга удалена.", "info")
    return redirect(url_for("moderator.services"))


# ---------- Specialists ----------

@moderator_bp.route("/specialists")
def specialists():
    salon = _current_salon()
    items = Specialist.query.filter_by(salon_id=salon.id)\
                            .order_by(Specialist.full_name).all()
    return render_template("moderator/specialists.html", salon=salon, specialists=items)


@moderator_bp.route("/specialists/new", methods=["GET", "POST"])
def specialist_new():
    salon = _current_salon()
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()[:150]
        specialization = request.form.get("specialization", "").strip()[:150]
        description = request.form.get("description", "").strip()[:2000]
        photo_url = request.form.get("photo_url", "").strip()[:300]
        if not full_name:
            flash("Укажите имя.", "danger")
        else:
            db.session.add(Specialist(salon_id=salon.id, full_name=full_name,
                                       specialization=specialization,
                                       description=description, photo_url=photo_url))
            db.session.commit()
            audit("SPECIALIST CREATED", target_type="salon", target_id=salon.id,
                  details=f"name={full_name}")
            flash("Специалист добавлен.", "success")
            return redirect(url_for("moderator.specialists"))
    return render_template("moderator/specialist_form.html", salon=salon, specialist=None)


@moderator_bp.route("/specialists/<int:specialist_id>/edit", methods=["GET", "POST"])
def specialist_edit(specialist_id):
    salon = _current_salon()
    specialist = Specialist.query.filter_by(id=specialist_id, salon_id=salon.id).first_or_404()
    if request.method == "POST":
        specialist.full_name = request.form.get("full_name", "").strip()[:150]
        specialist.specialization = request.form.get("specialization", "").strip()[:150]
        specialist.description = request.form.get("description", "").strip()[:2000]
        specialist.photo_url = request.form.get("photo_url", "").strip()[:300]
        specialist.is_active = bool(request.form.get("is_active"))
        db.session.commit()
        audit("SPECIALIST UPDATED", target_type="specialist", target_id=specialist.id)
        flash("Данные специалиста обновлены.", "success")
        return redirect(url_for("moderator.specialists"))
    return render_template("moderator/specialist_form.html", salon=salon, specialist=specialist)


@moderator_bp.route("/specialists/<int:specialist_id>/delete", methods=["POST"])
def specialist_delete(specialist_id):
    salon = _current_salon()
    specialist = Specialist.query.filter_by(id=specialist_id, salon_id=salon.id).first_or_404()
    db.session.delete(specialist)
    db.session.commit()
    audit("SPECIALIST DELETED", target_type="specialist", target_id=specialist_id)
    flash("Специалист удалён.", "info")
    return redirect(url_for("moderator.specialists"))


# ---------- Bookings ----------

@moderator_bp.route("/bookings")
def bookings():
    salon = _current_salon()
    status_filter = request.args.get("status")
    query = Booking.query.filter_by(salon_id=salon.id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    items = query.order_by(Booking.booking_datetime).all()
    return render_template("moderator/bookings.html", salon=salon, bookings=items,
                           status_filter=status_filter)


@moderator_bp.route("/bookings/<int:booking_id>/status", methods=["POST"])
def booking_update_status(booking_id):
    salon = _current_salon()
    booking = Booking.query.filter_by(id=booking_id, salon_id=salon.id).first_or_404()
    new_status = request.form.get("status")
    if new_status in ("pending", "confirmed", "cancelled", "completed"):
        booking.status = new_status
        db.session.commit()
        audit("BOOKING STATUS", target_type="booking", target_id=booking.id,
              details=f"status={new_status}")
        flash("Статус записи обновлён.", "success")
    return redirect(url_for("moderator.bookings"))


# ---------- Salon profile ----------

@moderator_bp.route("/salon", methods=["GET", "POST"])
def salon_edit():
    salon = _current_salon()
    regions = Region.query.order_by(Region.name).all()
    if request.method == "POST":
        salon.name = request.form.get("name", "").strip()[:150]
        salon.address = request.form.get("address", "").strip()[:255]
        salon.phone = request.form.get("phone", "").strip()[:30]
        salon.description = request.form.get("description", "").strip()[:2000]
        salon.photo_url = request.form.get("photo_url", "").strip()[:500]
        salon.latitude = request.form.get("latitude", type=float)
        salon.longitude = request.form.get("longitude", type=float)
        salon.city_id = request.form.get("city_id", type=int) or None

        files = request.files.getlist("photos")
        start_pos = SalonPhoto.query.filter_by(salon_id=salon.id).count()
        for idx, f in enumerate(files):
            rel = save_salon_photo(f, salon.id)
            if rel:
                db.session.add(SalonPhoto(salon_id=salon.id, url=rel,
                                          position=start_pos + idx))

        db.session.flush()
        if not salon.photo_url:
            first = SalonPhoto.query.filter_by(salon_id=salon.id)\
                                    .order_by(SalonPhoto.position).first()
            if first:
                salon.photo_url = first.url

        db.session.commit()
        audit("SALON UPDATED (moderator)", target_type="salon", target_id=salon.id)
        flash("Данные салона обновлены.", "success")
        return redirect(url_for("moderator.dashboard"))
    return render_template("moderator/salon_form.html", salon=salon, regions=regions)


@moderator_bp.route("/salon/photos/<int:photo_id>/delete", methods=["POST"])
def salon_photo_delete(photo_id):
    salon = _current_salon()
    photo = SalonPhoto.query.filter_by(id=photo_id, salon_id=salon.id).first_or_404()

    removed_url = photo.url
    delete_salon_photo_file(removed_url)

    db.session.delete(photo)
    db.session.flush()

    if salon.photo_url == removed_url:
        next_photo = (SalonPhoto.query
                      .filter_by(salon_id=salon.id)
                      .order_by(SalonPhoto.position)
                      .first())
        salon.photo_url = next_photo.url if next_photo else None

    db.session.commit()
    audit("PHOTO DELETED (moderator)", target_type="salon_photo", target_id=photo_id)
    flash("Фото удалено.", "info")
    return redirect(url_for("moderator.salon_edit"))