"""Deep-flow тесты админа: полный CRUD салона → услуги → специалисты → записи."""
from app.models import Salon, Service, Specialist, Booking, AuditLog, User


def test_full_salon_lifecycle(admin_client, db):
    # 1. Создать салон
    r = admin_client.post("/admin/salons/new", data={
        "name": "Deep Salon",
        "address": "ул. Глубокая, д. 1",
        "phone": "+7 000 111-22-33",
        "description": "Deep flow",
        "photo_url": "",
        "latitude": "55.0",
        "longitude": "37.0",
        "city_id": "",
    }, follow_redirects=True)
    assert r.status_code == 200

    salon = Salon.query.filter_by(name="Deep Salon").first()
    assert salon is not None

    # 2. Изменить
    r = admin_client.post(f"/admin/salons/{salon.id}/edit", data={
        "name": "Deep Salon Updated",
        "address": salon.address,
        "phone": salon.phone,
        "description": salon.description,
        "photo_url": "",
        "latitude": "55.0",
        "longitude": "37.0",
        "city_id": "",
        "is_active": "on",
    }, follow_redirects=True)
    assert r.status_code == 200
    assert Salon.query.get(salon.id).name == "Deep Salon Updated"

    # 3. Добавить услугу
    r = admin_client.post(f"/admin/salons/{salon.id}/services/new", data={
        "name": "Deep Service",
        "description": "Desc",
        "price": "1500",
        "duration_minutes": "45",
    }, follow_redirects=True)
    assert r.status_code == 200
    svc = Service.query.filter_by(name="Deep Service").first()
    assert svc is not None
    assert svc.salon_id == salon.id

    # 4. Изменить услугу
    r = admin_client.post(
        f"/admin/salons/{salon.id}/services/{svc.id}/edit",
        data={
            "name": "Deep Service Updated",
            "description": "Desc2",
            "price": "2000",
            "duration_minutes": "50",
            "is_active": "on",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    updated = Service.query.get(svc.id)
    assert updated.name == "Deep Service Updated"
    assert float(updated.price) == 2000.0

    # 5. Добавить специалиста
    r = admin_client.post(f"/admin/salons/{salon.id}/specialists/new", data={
        "full_name": "Deep Master",
        "specialization": "Барбер",
        "description": "Desc",
    }, follow_redirects=True)
    assert r.status_code == 200
    sp = Specialist.query.filter_by(full_name="Deep Master").first()
    assert sp is not None
    assert sp.salon_id == salon.id

    # 6. Изменить специалиста
    r = admin_client.post(
        f"/admin/salons/{salon.id}/specialists/{sp.id}/edit",
        data={
            "full_name": "Deep Master Updated",
            "specialization": "Топ-барбер",
            "description": "Best",
            "is_active": "on",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert Specialist.query.get(sp.id).full_name == "Deep Master Updated"

    # 7. Удалить услугу
    r = admin_client.post(
        f"/admin/salons/{salon.id}/services/{svc.id}/delete",
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert Service.query.get(svc.id) is None

    # 8. Удалить специалиста
    r = admin_client.post(
        f"/admin/salons/{salon.id}/specialists/{sp.id}/delete",
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert Specialist.query.get(sp.id) is None

    # 9. Удалить салон
    r = admin_client.post(f"/admin/salons/{salon.id}/delete",
                          follow_redirects=True)
    assert r.status_code == 200
    assert Salon.query.get(salon.id) is None


def test_audit_log_written_on_salon_create(admin_client, db):
    """Создание салона должно оставить след в audit_log."""
    before = AuditLog.query.count()
    admin_client.post("/admin/salons/new", data={
        "name": "Audit Salon",
        "address": "ул. Аудит, д. 1",
        "phone": "",
        "description": "",
        "photo_url": "",
        "latitude": "",
        "longitude": "",
        "city_id": "",
    }, follow_redirects=True)
    after = AuditLog.query.count()
    assert after > before

    entry = AuditLog.query.order_by(AuditLog.id.desc()).first()
    assert entry.action == "SALON CREATED"
    assert entry.target_type == "salon"


def test_audit_log_written_on_user_toggle(admin_client, db):
    # Найти клиента
    user = User.query.filter_by(email="client@test.local").first()
    assert user is not None
    assert user.is_active_flag is True

    admin_client.post(f"/admin/users/{user.id}/toggle_active",
                      follow_redirects=True)

    entry = AuditLog.query.order_by(AuditLog.id.desc()).first()
    assert entry.action == "USER TOGGLED"
    assert entry.target_type == "user"
    assert entry.target_id == user.id


def test_admin_can_assign_and_revoke_moderator(admin_client, db):
    # Создать обычного пользователя
    u = User(full_name="Обычный", email="plain@test.local",
             phone="+79009999999", role="client", phone_verified=True)
    u.set_password("pass123")
    db.session.add(u)
    db.session.commit()

    salon = Salon.query.first()

    # Назначить модератором
    r = admin_client.post(f"/admin/users/{u.id}/assign_moderator",
                          data={"salon_id": str(salon.id)},
                          follow_redirects=True)
    assert r.status_code == 200
    u_reloaded = User.query.get(u.id)
    assert u_reloaded.role == "moderator"
    assert u_reloaded.salon_id == salon.id

    # Снять
    r = admin_client.post(f"/admin/users/{u.id}/revoke_moderator",
                          follow_redirects=True)
    assert r.status_code == 200
    u_reloaded = User.query.get(u.id)
    assert u_reloaded.role == "client"
    assert u_reloaded.salon_id is None


def test_admin_cannot_touch_admin_account(admin_client, db):
    """Нельзя разжаловать или заблокировать админа."""
    admin = User.query.filter_by(email="admin@test.local").first()
    r = admin_client.post(f"/admin/users/{admin.id}/toggle_active",
                          follow_redirects=True)
    assert r.status_code == 200
    # Флаг остался True
    assert User.query.get(admin.id).is_active_flag is True

    r = admin_client.post(f"/admin/users/{admin.id}/revoke_moderator",
                          follow_redirects=True)
    # Должно быть 400 или без изменений
    assert User.query.get(admin.id).role == "admin"


def test_admin_bookings_status_change(admin_client, db):
    """Админ может менять статус любой записи."""
    from datetime import datetime
    salon = Salon.query.first()
    service = Service.query.filter_by(salon_id=salon.id).first()
    specialist = Specialist.query.filter_by(salon_id=salon.id).first()
    client_user = User.query.filter_by(email="client@test.local").first()

    booking = Booking(
        user_id=client_user.id, salon_id=salon.id,
        service_id=service.id, specialist_id=specialist.id,
        booking_datetime=datetime(2030, 1, 1, 12, 0),
        status="pending",
    )
    db.session.add(booking)
    db.session.commit()

    r = admin_client.post(f"/admin/bookings/{booking.id}/status",
                          data={"status": "confirmed"},
                          follow_redirects=True)
    assert r.status_code == 200
    assert Booking.query.get(booking.id).status == "confirmed"