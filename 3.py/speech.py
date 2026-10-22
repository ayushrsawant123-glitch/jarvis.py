"""Speech synthesis and recognition helpers."""

import sys
import speech_recognition as sr
import pyttsx3

from config import SPEECH_RATE, WAKE_WORD

sys.stdout.reconfigure(encoding="utf-8")

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        _engine.setProperty("rate", SPEECH_RATE)
    return _engine


def speak(text):
    """Speak text aloud. Safe to call even if TTS fails."""
    if not text:
        return
    try:
        engine = _get_engine()
        engine.say(text)
        engine.runAndWait()
    except Exception as exc:
        print(f"[TTS error] {exc}")
        print(f"JARVIS: {text}")


def listen(timeout=None, phrase_time_limit=None):
    """
    Listen from microphone and return lowercase text, or None on failure.
    Does not speak error messages — caller decides how to report them.
    """
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(
                source, timeout=timeout, phrase_time_limit=phrase_time_limit
            )
    except sr.WaitTimeoutError:
        return None, "I did not hear anything. Please try again."
    except OSError as exc:
        return None, f"Microphone not available: {exc}"
    except Exception as exc:
        return None, f"Microphone error: {exc}"

    try:
        query = recognizer.recognize_google(audio)
        print(f"You said: {query}")
        return query.lower(), None
    except sr.UnknownValueError:
        return None, "Sorry, I could not understand what you said."
    except sr.RequestError:
        return None, "Speech service is unavailable. Check your internet connection."
    except Exception as exc:
        return None, f"Recognition error: {exc}"


def listen_or_none():
    """Backward-compatible helper: returns query string or None."""
    query, error = listen()
    if error:
        speak(error)
    return query


def welcome():
    speak("Welcome back Sir! How can I assist you?")


def wait_for_wake_word():
    while True:
        print("Waiting for wake word...")
        query, _ = listen()
        if query and WAKE_WORD in query:
            speak("Yes sir, I am listening")
            return
