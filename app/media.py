"""Общие функции для работы с загружаемыми файлами."""
import os
import uuid
import shutil

from flask import current_app

ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "gif"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def save_salon_photo(file, salon_id: int):
    """Сохраняет файл в static/uploads/salons/<salon_id>/<uuid>.<ext>.
    Возвращает относительный путь '<salon_id>/<filename>' или None."""
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename):
        return None

    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], str(salon_id))
    os.makedirs(folder, exist_ok=True)

    ext = file.filename.rsplit(".", 1)[1].lower()
    name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(folder, name)
    file.save(path)
    return f"{salon_id}/{name}"


def delete_salon_photo_file(rel_url: str) -> None:
    """Удаляет файл с диска, если он локальный."""
    if not rel_url or rel_url.startswith(("http://", "https://")):
        return
    full = os.path.join(current_app.config["UPLOAD_FOLDER"], rel_url)
    if os.path.isfile(full):
        try:
            os.remove(full)
        except OSError:
            pass


def delete_salon_folder(salon_id: int) -> None:
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], str(salon_id))
    if os.path.isdir(folder):
        shutil.rmtree(folder, ignore_errors=True)