# Развёртывание Vibe

## Выбор WSGI-сервера

- **Linux (прод):** gunicorn + nginx.
- **Windows (разработка/демонстрация):** waitress.

## Windows: запуск через waitress

Установка:
```powershell
pip install waitress

## Предварительно

- VPS с Ubuntu 22.04.
- Домен, направленный на IP сервера (A-запись).
- Доступ по SSH.

## Шаг 1. Системные пакеты

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip nginx certbot python3-certbot-nginx git