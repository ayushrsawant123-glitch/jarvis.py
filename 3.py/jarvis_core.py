"""Voice-mode JARVIS loop."""

from auth import authenticate
from commands import process_command
from speech import welcome, listen_or_none, speak


def jarvis():
    """Start full voice assistant session (password + command loop)."""
    welcome()
    ok, msg = authenticate()
    if not ok:
        speak("Authentication failed. Stopping JARVIS.")
        return

    print(f"[auth] {msg}")

    while True:
        query = listen_or_none()
        if not query:
            continue

        result = process_command(query, speak_reply=True, ask_fn=listen_or_none)
        print(f"[command] {query} -> {result.get('reply')}")

        if "exit" in query or "bye" in query:
            break
