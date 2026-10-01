# Vibe — сеть барбершопов

Учебный проект: система онлайн-записи в парикмахерские, барбершопы и салоны красоты.

## Стек

- Python 3.11+
- Flask 3.0
- SQLAlchemy + SQLite
- Flask-Login, Flask-WTF (CSRF), Flask-Limiter
- Bootstrap 5, Leaflet (карты)

## Возможности

- Регистрация с подтверждением телефона (код в консоль — демо-режим)
- Вход по e-mail или телефону
- Восстановление пароля по коду
- Поиск салонов по городу и адресу
- Автоопределение города по геолокации
- Онлайн-запись на услугу к специалисту
- Личный кабинет с историей записей
- Кабинеты модератора и администратора
- Загрузка фотографий салонов
- Логирование действий, ошибок и событий безопасности
- Защита: CSRF, rate limit, DDoS-гард, хеширование паролей

## Быстрый старт

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Полученный ключ вставьте в `.env` вместо `replace-me-with-random-hex`.

```powershell
python seed.py
python run.py
```

Откройте: **http://127.0.0.1:5000**

## Тестовые аккаунты

| Роль | Логин | Пароль |
|------|-------|--------|
| Администратор | admin@barber.local | admin123 |
| Модератор | moderator@barber.local | moder123 |
| Клиент | client@barber.local | client123 |

Вход возможен также по телефону: `+79000000001`, `+79000000002`, `+79000000003` (те же пароли).

## Структура

```
barbershop/
├── app/                    # приложение Flask
│   ├── __init__.py         # фабрика create_app
│   ├── models.py           # модели БД
│   ├── auth.py             # вход, регистрация, сброс пароля
│   ├── main.py             # главная, салоны, записи
│   ├── admin.py            # админ-панель
│   ├── moderator.py        # кабинет модератора
│   ├── security.py         # DDoS-гард
│   ├── sms.py              # отправка кодов
│   ├── media_sync.py       # синхронизация фото
│   ├── logging_config.py   # логирование
│   └── regions.py          # справочник городов
├── templates/              # HTML-шаблоны
├── static/
│   ├── css/style.css
│   ├── img/logo.png
│   └── uploads/salons/     # фото салонов по id
├── logs/                   # логи (создаётся автоматически)
├── seed.py                 # наполнение БД
├── run.py                  # запуск
├── requirements.txt
├── .env.example
└── README.md
```

## Логи

Пишутся в `logs/`:

- `app.log` — действия пользователей
- `errors.log` — ошибки
- `security.log` — логины, баны, коды

## Примечания

- **SMS в демо-режиме** — коды печатаются в консоль сервера.
- **Геолокация** работает только на `localhost` или HTTPS.
- **Фото салонов** кладутся в `static/uploads/salons/<id>/` — синхронизируются при старте.

## Лицензия

Учебный проект.
