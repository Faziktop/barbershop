"""
Фикстуры для тестов.
Изолированная БД в памяти, тестовые клиенты и пользователи разных ролей.
"""
import os
import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")

from app import create_app, db as _db
from app.models import (
    User, Region, City, Salon, Service, Specialist,
    ROLE_ADMIN, ROLE_MODERATOR, ROLE_CLIENT,
)


@pytest.fixture(scope="session")
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "RATELIMIT_ENABLED": False,
    })
    with app.app_context():
        _db.create_all()
        _seed_users()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    with app.app_context():
        yield _db


def _seed_users():
    """Минимальный набор: регион, город, салон, услуга, специалист, 3 пользователя."""
    region = Region(name="Тестовый регион")
    _db.session.add(region)
    _db.session.flush()

    city = City(region_id=region.id, name="Тестоград",
                latitude=55.0, longitude=37.0)
    _db.session.add(city)
    _db.session.flush()

    salon = Salon(city_id=city.id, name="Test Salon",
                  address="ул. Тестовая, д. 1",
                  latitude=55.0, longitude=37.0)
    _db.session.add(salon)
    _db.session.flush()

    service = Service(salon_id=salon.id, name="Стрижка",
                      price=1000, duration_minutes=40)
    specialist = Specialist(salon_id=salon.id, full_name="Иван Тестов",
                            specialization="Барбер")
    _db.session.add_all([service, specialist])

    admin = User(full_name="Админ", email="admin@test.local",
                 phone="+79001111111", role=ROLE_ADMIN, phone_verified=True)
    admin.set_password("admin123")
    moderator = User(full_name="Модератор", email="mod@test.local",
                     phone="+79002222222", role=ROLE_MODERATOR,
                     salon_id=salon.id, phone_verified=True)
    moderator.set_password("moder123")
    client = User(full_name="Клиент", email="client@test.local",
                  phone="+79003333333", role=ROLE_CLIENT, phone_verified=True)
    client.set_password("client123")
    _db.session.add_all([admin, moderator, client])
    _db.session.commit()


def _login(client, login_value, password):
    """Помощник: авторизация через реальный POST /login."""
    return client.post("/login", data={
        "login": login_value,
        "password": password,
    }, follow_redirects=False)


@pytest.fixture()
def admin_client(client):
    _login(client, "admin@test.local", "admin123")
    return client


@pytest.fixture()
def mod_client(client):
    _login(client, "mod@test.local", "moder123")
    return client


@pytest.fixture()
def user_client(client):
    _login(client, "client@test.local", "client123")
    return client