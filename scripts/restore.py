"""
Восстановление БД и файлов из бэкапа.

Использование:
    python scripts/restore.py backups/db_20261001_120000.sqlite
    python scripts/restore.py backups/db_20261001_120000.sqlite backups/uploads_20261001_120000.tar.gz

Перед восстановлением текущие данные сохраняются в backups/pre_restore_*.
"""
import os
import sys
import shutil
import sqlite3
import tarfile
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", BASE_DIR / "backups"))
DB_PATH = BASE_DIR / "barbershop.db"
UPLOADS_DIR = BASE_DIR / "static" / "uploads" / "salons"


def _ts():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def _confirm(prompt: str) -> bool:
    return input(prompt + " [yes/no]: ").strip().lower() == "yes"


def _safe_copy_current():
    """Копирует текущие данные перед восстановлением."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = _ts()

    if DB_PATH.exists():
        dst = BACKUP_DIR / f"pre_restore_db_{ts}.sqlite"
        src_conn = sqlite3.connect(str(DB_PATH))
        dst_conn = sqlite3.connect(str(dst))
        with dst_conn:
            src_conn.backup(dst_conn)
        src_conn.close()
        dst_conn.close()
        print(f"[restore] Текущая БД сохранена: {dst}")

    if UPLOADS_DIR.exists():
        dst = BACKUP_DIR / f"pre_restore_uploads_{ts}.tar.gz"
        with tarfile.open(dst, "w:gz") as tar:
            tar.add(UPLOADS_DIR, arcname="salons")
        print(f"[restore] Текущие uploads сохранены: {dst}")


def _restore_db(src: Path):
    if not src.exists():
        print(f"[restore] Файл не найден: {src}")
        sys.exit(1)

    # Проверяем, что это валидная SQLite-база
    try:
        conn = sqlite3.connect(str(src))
        conn.execute("SELECT name FROM sqlite_master LIMIT 1")
        conn.close()
    except sqlite3.DatabaseError as e:
        print(f"[restore] Файл не является SQLite БД: {e}")
        sys.exit(1)

    if DB_PATH.exists():
        DB_PATH.unlink()

    # Копируем через backup API (безопасно)
    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(DB_PATH))
    with dst_conn:
        src_conn.backup(dst_conn)
    src_conn.close()
    dst_conn.close()
    print(f"[restore] БД восстановлена из {src}")


def _restore_uploads(archive: Path):
    if not archive.exists():
        print(f"[restore] Архив не найден: {archive}")
        sys.exit(1)

    if UPLOADS_DIR.exists():
        shutil.rmtree(UPLOADS_DIR)

    UPLOADS_DIR.parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive, "r:gz") as tar:
        # Безопасная распаковка — защита от path traversal
        base = UPLOADS_DIR.parent.resolve()
        for member in tar.getmembers():
            target = (base / member.name).resolve()
            if not str(target).startswith(str(base)):
                print(f"[restore] Пропущен небезопасный путь: {member.name}")
                continue
        tar.extractall(UPLOADS_DIR.parent)
    print(f"[restore] Uploads восстановлены из {archive}")


def main():
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python scripts/restore.py backups/db_YYYYMMDD_HHMMSS.sqlite")
        print("  python scripts/restore.py <db_file> [uploads_archive.tar.gz]")
        sys.exit(1)

    db_file = Path(sys.argv[1])
    uploads_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    print("[restore] Планируется восстановить:")
    print(f"  БД:       {db_file}")
    if uploads_file:
        print(f"  Uploads:  {uploads_file}")

    if not _confirm("Продолжить? Текущие данные будут сохранены в backups/pre_restore_*"):
        print("[restore] Отменено.")
        sys.exit(0)

    _safe_copy_current()
    _restore_db(db_file)
    if uploads_file:
        _restore_uploads(uploads_file)

    print("[restore] Готово. Перезапустите приложение.")


if __name__ == "__main__":
    main()