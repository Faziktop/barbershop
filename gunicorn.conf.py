"""
Конфиг gunicorn для Vibe.

Запуск:
    gunicorn -c gunicorn.conf.py wsgi:application
"""
import multiprocessing
import os

# Адрес привязки — nginx будет проксировать сюда
bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")

# Воркеры: 2 * CPU + 1 (стандартная формула)
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# Потоки на воркер (для I/O-bound операций — БД, файлы)
threads = int(os.environ.get("GUNICORN_THREADS", "4"))

# Класс воркера — sync для Flask
worker_class = "sync"

# Таймаут запроса
timeout = 60

# Плавный перезапуск
graceful_timeout = 30

# Keepalive
keepalive = 5

# Логи — в stdout/stderr (их подхватит systemd)
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")

# Не менять владельца
user = None
group = None

# Имя процесса
proc_name = "vibe"

# Максимум запросов до перезапуска воркера (защита от утечек памяти)
max_requests = 1000
max_requests_jitter = 100