"""
Run PDF Chatbot backend API + Streamlit UI with a single command.
  python run.py

Backend: http://localhost:8000  (API + docs at /docs)
UI:      http://localhost:8501 (Streamlit)

Run from the project root (directory containing run.py and app/).
"""

import atexit
import os
import subprocess
import sys
import threading
import time

# Add project root to path first so "app" can be imported from anywhere
ROOT = os.path.realpath(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

_streamlit = None
BACKEND_PORT = 8000


def _run_backend():
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=BACKEND_PORT,
        log_level="info",
    )


def kill_streamlit():
    global _streamlit
    if _streamlit and _streamlit.poll() is None:
        _streamlit.terminate()
        try:
            _streamlit.wait(timeout=3)
        except Exception:
            _streamlit.kill()
    _streamlit = None


def main():
    global _streamlit
    try:
        import app.main
    except Exception as e:
        print("Backend import failed:", e)
        print("Project root:", ROOT)
        print("sys.path[0]:", sys.path[0] if sys.path else "empty")
        sys.exit(1)

    try:
        import streamlit
    except ImportError:
        print("Streamlit is not installed. Run: pip install streamlit")
        print("Or install all deps: pip install -r requirements.txt")
        sys.exit(1)

    backend_thread = threading.Thread(target=_run_backend, daemon=True)
    backend_thread.start()
    time.sleep(1.5)
    if not backend_thread.is_alive():
        print("Backend failed to start (e.g. port 8000 in use).")
        sys.exit(1)

    _streamlit = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
            "--server.port", "8501",
            "--server.headless", "true",
        ],
        cwd=ROOT,
    )

    atexit.register(kill_streamlit)
    try:
        import signal
        signal.signal(signal.SIGINT, lambda s, f: (kill_streamlit(), sys.exit(0)))
        signal.signal(signal.SIGTERM, lambda s, f: (kill_streamlit(), sys.exit(0)))
    except AttributeError:
        pass

    print("Backend: http://localhost:8000  |  UI: http://localhost:8501")
    _streamlit.wait()
    kill_streamlit()


if __name__ == "__main__":
    main()
