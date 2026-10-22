"""JARVIS configuration — change settings here without editing core logic."""

# Voice password (say this after Start JARVIS)
VOICE_PASSWORD = "open jarvis"

# Wake word (optional future use)
WAKE_WORD = "jarvis"

# Speech
SPEECH_RATE = 150

# Auth options
SKIP_FACE_LOGIN = True  # set False to require camera check
FACE_CAPTURE_MS = 2000

# Flask
HOST = "127.0.0.1"
PORT = 5000
DEBUG = True
OPEN_BROWSER_ON_START = True

# Simple chatbot phrases
CHATBOT_RESPONSES = {
    "hello": "Hello Sir! How can I help you?",
    "how are you": "I'm just a virtual assistant, but I'm doing great! How can I assist you?",
    "who are you": "I am Jarvis, your personal AI assistant.",
    "thank you": "You're welcome Sir!",
}
