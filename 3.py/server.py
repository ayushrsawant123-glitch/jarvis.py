"""
Backward-compatible entry point.

Prefer:  python app.py
Also OK: python server.py
"""

from app import app, main

if __name__ == "__main__":
    main()
