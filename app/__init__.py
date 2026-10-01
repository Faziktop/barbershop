import os

from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from sqlalchemy import event
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Пожалуйста, войдите в систему."
login_manager.login_message_category = "warning"

csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per day", "500 per hour"],
    storage_uri=os.environ.get("RATELIMIT_STORAGE", "memory://"),
)


@event.listens_for(Engine, "connect")
def _sqlite_pragma(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass


def create_app():
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    app = Flask(__name__)

    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY не задан. Создайте файл .env в корне проекта "
            "и добавьте строку SECRET_KEY=<ваш-ключ>"
        )
    app.config["SECRET_KEY"] = secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(basedir, "barbershop.db"),
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    secure_cookie = os.environ.get("COOKIE_SECURE", "0") == "1"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = secure_cookie
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SECURE"] = secure_cookie
    app.config["WTF_CSRF_TIME_LIMIT"] = None

    app.config["UPLOAD_FOLDER"] = os.path.join(basedir, "static", "uploads", "salons")
    app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    from .logging_config import configure_logging
    configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    from . import models  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))

    from .auth import auth_bp
    from .main import main_bp
    from .moderator import moderator_bp
    from .admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(moderator_bp, url_prefix="/moderator")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.context_processor
    def inject_globals():
        from datetime import datetime
        return {"now": datetime.utcnow()}

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(self)"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' "
            "  https://cdn.jsdelivr.net https://unpkg.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        return response

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        from werkzeug.exceptions import HTTPException
        from .alerts import send_alert
        if isinstance(e, HTTPException):
            if e.code >= 500:
                app.logger.error(f"HTTP {e.code}: {e.description}", exc_info=True)
                send_alert(f"HTTP {e.code}", f"path={request.path}")
            return e
        app.logger.exception("Необработанное исключение")
        send_alert("Необработанное исключение", f"path={request.path}")
        return "Внутренняя ошибка сервера", 500

    with app.app_context():
        from .media_sync import sync_salon_photos, sync_all_cover_covers
        try:
            sync_salon_photos(app)
            sync_all_cover_covers(app)
        except Exception as e:
            app.logger.exception(f"[SYNC] ошибка: {e}")

    app.logger.info("=== Приложение создано ===")
    return app