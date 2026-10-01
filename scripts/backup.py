"""
Резервное копирование БД и загруженных файлов.
Запуск: python scripts/backup.py
Windows Task Scheduler / cron — ежедневно.
"""
import os
import sqlite3
import tarfile
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", BASE_DIR / "backups"))
KEEP_DAYS = int(os.environ.get("BACKUP_KEEP_DAYS", "30"))

DB_PATH = BASE_DIR / "barbershop.db"
UPLOADS_DIR = BASE_DIR / "static" / "uploads" / "salons"


def backup_db(target_dir: Path):
    if not DB_PATH.exists():
        print(f"[backup] БД не найдена: {DB_PATH}")
        return
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = target_dir / f"db_{ts}.sqlite"
    src_conn = sqlite3.connect(str(DB_PATH))
    dst_conn = sqlite3.connect(str(dst))
    with dst_conn:
        src_conn.backup(dst_conn)
    src_conn.close()
    dst_conn.close()
    print(f"[backup] БД: {dst}")


def backup_uploads(target_dir: Path):
    if not UPLOADS_DIR.exists():
        print(f"[backup] uploads нет, пропускаю")
        return
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = target_dir / f"uploads_{ts}.tar.gz"
    with tarfile.open(dst, "w:gz") as tar:
        tar.add(UPLOADS_DIR, arcname="salons")
    print(f"[backup] uploads: {dst}")


def cleanup_old(target_dir: Path):
    cutoff = datetime.datetime.now() - datetime.timedelta(days=KEEP_DAYS)
    removed = 0
    for f in target_dir.iterdir():
        if not f.is_file():
            continue
        mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
        if mtime < cutoff:
            f.unlink()
            removed += 1
    if removed:
        print(f"[backup] Удалено старых: {removed}")


def run():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[backup] Папка: {BACKUP_DIR}")
    backup_db(BACKUP_DIR)
    backup_uploads(BACKUP_DIR)
    cleanup_old(BACKUP_DIR)
    print("[backup] Готово.")


if __name__ == "__main__":
    run()