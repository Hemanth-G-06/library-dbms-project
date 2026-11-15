import os
import sys
import webbrowser
import threading
import time
import uvicorn

# Ensure the root project directory is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.main import app

def open_browser():
    time.sleep(1.2)
    try:
        webbrowser.open("http://127.0.0.1:8000")
    except Exception:
        pass

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" 📚 SMART LIBRARY MANAGEMENT SYSTEM (DBMS PROJECT)")
    print("=" * 60)
    print(" [*] Server starting at: http://127.0.0.1:8000")
    print(" [*] Web Portal:        http://127.0.0.1:8000/")
    print(" [*] Login Portal:      http://127.0.0.1:8000/login")
    print(" [*] API Documentation: http://127.0.0.1:8000/docs")
    print("=" * 60 + "\n")

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

