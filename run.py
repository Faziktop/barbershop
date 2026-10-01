"""
Запуск приложения. Хост, порт и debug берутся из ENV.

Продакшен: DEBUG=0 HOST=127.0.0.1 PORT=5000 python run.py
Отладка:   python dev.py
"""
import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("DEBUG", "0") == "1"

    print(f"\n=== Vibe ===")
    print(f"Откройте: http://{host}:{port}")
    print(f"Debug: {'ON' if debug else 'OFF'}")
    print("============\n")

    app.run(host=host, port=port, debug=debug)