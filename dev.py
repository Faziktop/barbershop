"""
Отладочный запуск с автоперезагрузкой.
WARNING: debug=True даёт RCE через Werkzeug debugger.
Использовать только локально, не на сервере.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    print("\n=== Vibe (dev) ===")
    print("Откройте: http://127.0.0.1:5000")
    print("WARNING: debug=True — только для локальной отладки!")
    print("==================\n")
    app.run(debug=True, host="127.0.0.1", port=5000)