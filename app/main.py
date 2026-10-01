import math
from datetime import datetime, date

from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, abort, jsonify)
from flask_login import login_required, current_user
from sqlalchemy import text

from . import db, limiter
from .models import (Salon, Service, Specialist, Booking, City, Region,
                     STATUS_CANCELLED)
from .audit import audit
from .services.bookings import (
    get_available_slots, create_booking, BookingError,
)

main_bp = Blueprint("main", __name__)


@main_bp.route("/health")
def health():
    db_ok = True
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return jsonify({"status": "ok" if db_ok else "degraded", "db": db_ok}), \
        (200 if db_ok else 503)


@main_bp.route("/")
def index():
    q = (request.args.get("q") or "").strip()
    city_id = request.args.get("city_id", type=int)
    view = request.args.get("view", "cards")
    if view not in ("cards", "list"):
        view = "cards"

    query = Salon.query.filter_by(is_active=True)
    if city_id:
        query = query.filter_by(city_id=city_id)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Salon.address.ilike(like),
                                    Salon.name.ilike(like),
                                    Salon.description.ilike(like)))
    salons = query.order_by(Salon.name).all()
    regions = Region.query.order_by(Region.name).all()

    return render_template("index.html", salons=salons, regions=regions,
                           q=q, selected_city_id=city_id, view=view)


@main_bp.route("/api/cities")
@limiter.limit("60 per minute")
def api_cities():
    q = (request.args.get("q") or "").strip().lower()
    all_cities = City.query.order_by(City.name).all()
    if q:
        all_cities = [c for c in all_cities if q in (c.name or "").strip().lower()]
    all_cities = all_cities[:30]
    return jsonify([{"id": c.id, "name": c.name,
                     "region": c.region.name if c.region else ""}
                    for c in all_cities])


@main_bp.route("/api/find-city")
@limiter.limit("30 per minute")
def api_find_city():
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"ok": False}), 400

    cities = City.query.all()
    if not cities:
        return jsonify({"ok": False})

    def hv(c):
        if c.latitude is None or c.longitude is None:
            return 1e18
        R = 6371.0
        phi1 = math.radians(lat)
        phi2 = math.radians(c.latitude)
        dphi = math.radians(c.latitude - lat)
        dl = math.radians(c.longitude - lon)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
        return 2 * R * math.asin(math.sqrt(a))

    best = min(cities, key=hv)
    dist_km = hv(best)
    if dist_km > 60:
        return jsonify({"ok": False, "nearest": best.name,
                        "distance_km": round(dist_km, 1)})
    return jsonify({"ok": True, "city_id": best.id, "city_name": best.name,
                    "distance_km": round(dist_km, 1)})


@main_bp.route("/salon/<int:salon_id>")
def salon_detail(salon_id):
    salon = Salon.query.get_or_404(salon_id)
    services = Service.query.filter_by(salon_id=salon.id, is_active=True).all()
    specialists = Specialist.query.filter_by(salon_id=salon.id, is_active=True).all()
    return render_template("salon_detail.html", salon=salon,
                           services=services, specialists=specialists)


@main_bp.route("/salon/<int:salon_id>/book", methods=["GET", "POST"])
@login_required
@limiter.limit("30 per minute;200 per hour", methods=["POST"])
def book(salon_id):
    salon = Salon.query.get_or_404(salon_id)
    services = Service.query.filter_by(salon_id=salon.id, is_active=True).all()
    specialists = Specialist.query.filter_by(salon_id=salon.id, is_active=True).all()

    selected_service_id = request.values.get("service_id", type=int)
    selected_specialist_id = request.values.get("specialist_id", type=int)
    selected_date_str = request.values.get("date")
    try:
        selected_date = (datetime.strptime(selected_date_str, "%Y-%m-%d").date()
                         if selected_date_str else date.today())
    except ValueError:
        selected_date = date.today()
    if selected_date < date.today():
        selected_date = date.today()

    available_slots = []
    if selected_specialist_id:
        available_slots = get_available_slots(selected_specialist_id, selected_date)

    if request.method == "POST":
        try:
            booking = create_booking(
                user_id=current_user.id,
                salon_id=salon.id,
                service_id=request.form.get("service_id", type=int),
                specialist_id=request.form.get("specialist_id", type=int),
                slot_str=request.form.get("slot"),
                note=request.form.get("note", "").strip()[:500],
            )
            audit("BOOKING CREATED", target_type="booking", target_id=booking.id,
                  details=f"salon={salon.id}")
            flash("Заявка отправлена.", "success")
            return redirect(url_for("main.profile"))
        except BookingError as e:
            flash(str(e), "danger")

    return render_template("booking_form.html", salon=salon, services=services,
                           specialists=specialists,
                           selected_service_id=selected_service_id,
                           selected_specialist_id=selected_specialist_id,
                           selected_date=selected_date, available_slots=available_slots)


@main_bp.route("/profile")
@login_required
def profile():
    bookings = (Booking.query.filter_by(user_id=current_user.id)
                .order_by(Booking.booking_datetime.desc()).all())
    return render_template("profile.html", bookings=bookings)


@main_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        current_user.full_name = request.form.get("full_name",
                                                  current_user.full_name).strip()[:150]
        new_phone = request.form.get("phone", current_user.phone or "").strip()[:30]
        if new_phone != (current_user.phone or ""):
            current_user.phone = new_phone
            current_user.phone_verified = False
        new_password = request.form.get("password", "")
        if new_password:
            if len(new_password) < 6:
                flash("Пароль минимум 6 символов.", "danger")
                return render_template("edit_profile.html")
            current_user.set_password(new_password)
        db.session.commit()
        audit("PROFILE UPDATED", target_type="user", target_id=current_user.id)
        flash("Профиль обновлён.", "success")
        return redirect(url_for("main.profile"))
    return render_template("edit_profile.html")


@main_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        abort(403)
    if booking.status in ("pending", "confirmed"):
        booking.status = STATUS_CANCELLED
        db.session.commit()
        audit("BOOKING CANCELLED", target_type="booking", target_id=booking.id)
        flash("Запись отменена.", "info")
    else:
        flash("Эту запись нельзя отменить.", "warning")
    return redirect(url_for("main.profile"))


@main_bp.route("/rules")
def rules():
    return render_template("rules.html")


@main_bp.route("/contacts")
def contacts():
    return render_template("contacts.html")