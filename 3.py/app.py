"""
JARVIS Flask backend — single clean entry point.

Run:
    python app.py
"""

import os
import threading
import webbrowser

from flask import Flask, jsonify, request, send_from_directory

from auth import authenticate
from config import HOST, PORT, DEBUG, OPEN_BROWSER_ON_START
from commands import process_command
from jarvis_core import jarvis

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=BASE_DIR, template_folder=BASE_DIR)

_jarvis_lock = threading.Lock()
_jarvis_running = False


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "main.html")


@app.route("/welcome")
def welcome_page():
    path = os.path.join(BASE_DIR, "welcome.html")
    if os.path.exists(path):
        return send_from_directory(BASE_DIR, "welcome.html")
    return jsonify({"message": "welcome.html not found"}), 404


@app.route("/start_jarvis", methods=["POST"])
def start_jarvis_route():
    """Start the voice JARVIS loop in a background thread."""
    global _jarvis_running

    with _jarvis_lock:
        if _jarvis_running:
            return jsonify({"status": "JARVIS already running"})
        _jarvis_running = True

    def _runner():
        global _jarvis_running
        try:
            jarvis()
        finally:
            with _jarvis_lock:
                _jarvis_running = False

    threading.Thread(target=_runner, daemon=True).start()
    return jsonify({"status": "JARVIS started!"})


@app.route("/auth", methods=["POST"])
def auth_route():
    """
    Text auth check.
    Body JSON: { "password": "open jarvis", "skip_face": true }
    """
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")
    skip_face = data.get("skip_face")
    ok, message = authenticate(password_text=password, skip_face=skip_face)
    return jsonify({"ok": ok, "message": message}), (200 if ok else 401)


@app.route("/command", methods=["POST"])
@app.route("/speak", methods=["POST"])
def command_route():
    """
    Text command API (same engine as voice).

    Body JSON examples:
      { "text": "what is the time" }
      { "text": "joke" }
      { "text": "search wikipedia", "topic": "Python" }
      { "text": "calculate", "expression": "12 * 8" }
      { "text": "battery" }

    Optional: "speak": true  — also speak the reply aloud
    """
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or data.get("command") or "").strip()
    speak_reply = bool(data.get("speak", False))

    if not text:
        return jsonify({"ok": False, "reply": "Missing 'text' field."}), 400

    extras = {
        k: v
        for k, v in data.items()
        if k not in {"text", "command", "speak"}
    }

    result = process_command(text, speak_reply=speak_reply, extras=extras)
    status = 200 if result.get("ok", True) else 400
    return jsonify(result), status


@app.route("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "jarvis_running": _jarvis_running,
            "endpoints": ["/", "/health", "/start_jarvis", "/auth", "/command", "/speak"],
        }
    )


def main():
    if OPEN_BROWSER_ON_START:
        threading.Timer(
            1.5, lambda: webbrowser.open(f"http://{HOST}:{PORT}/")
        ).start()
    # use_reloader=False avoids double-threads / port conflicts
    app.run(host=HOST, port=PORT, debug=DEBUG, use_reloader=False)


if __name__ == "__main__":
    main()
