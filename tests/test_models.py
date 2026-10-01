"""Тесты моделей: пользователи, салоны, услуги, записи."""
from app.models import User, Salon, Service, Specialist, ROLE_ADMIN


def test_password_hashing(db):
    u = User(full_name="Test", email="x@y.z", role=ROLE_ADMIN)
    u.set_password("secret123")
    assert u.password_hash != "secret123"
    assert u.check_password("secret123")
    assert not u.check_password("wrong")


def test_user_role_helpers(db):
    u = User(full_name="A", email="a@a.a", role=ROLE_ADMIN)
    assert u.is_admin()
    assert not u.is_moderator()
    assert not u.is_client()


def test_salon_photo_src_none(db):
    s = Salon(name="Test", address="addr")
    assert s.photo_src is None


def test_salon_photo_src_local(db):
    s = Salon(name="Test", address="addr", photo_url="5/abc.jpg")
    assert s.photo_src == "/static/uploads/salons/5/abc.jpg"


def test_salon_photo_src_external(db):
    s = Salon(name="Test", address="addr",
              photo_url="https://example.com/x.jpg")
    assert s.photo_src == "https://example.com/x.jpg"


def test_service_price_and_duration(db):
    s = Service(name="X", price=500, duration_minutes=30)
    assert s.price == 500
    assert s.duration_minutes == 30