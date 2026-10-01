"""
Фикстуры для тестов.

Создаём изолированную БД в памяти, тестового клиента Flask
и несколько пользователей с разными ролями.
"""
import os
import pytest

# Переопределяем окружение до импорта приложения
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")

from app import create_app, db as _db
from app.models import (
    User, Region, City, Salon, Service, Specialist,
    ROLE_ADMIN, ROLE_MODERATOR, ROLE_CLIENT,
)


@pytest.fixture(scope="session")
def app():
    """Создаём приложение с БД в памяти."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,      # для тестов CSRF отключаем
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "RATELIMIT_ENABLED": False,     # чтобы rate limit не мешал
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
    """Минимальный набор данных: админ, модератор, клиент, салон."""
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


@pytest.fixture()
def admin_client(client):
    """Клиент, вошедший как админ."""
    with client.session_transaction() as sess:
        # Flask-Login хранит user_id в сессии
        sess["_user_id"] = "1"
        sess["_fresh"] = True
    return client


@pytest.fixture()
def mod_client(client):
    with client.session_transaction() as sess:
        sess["_user_id"] = "2"
        sess["_fresh"] = True
    return client


@pytest.fixture()
def user_client(client):
    with client.session_transaction() as sess:
        sess["_user_id"] = "3"
        sess["_fresh"] = True
    return client