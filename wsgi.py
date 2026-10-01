"""
WSGI-точка входа для gunicorn / uWSGI.

Запуск через gunicorn:
    gunicorn -c gunicorn.conf.py wsgi:application
"""
from app import create_app

application = create_app()

# Для запуска через `python wsgi.py` (в отладке)
if __name__ == "__main__":
    import os
    application.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
    )