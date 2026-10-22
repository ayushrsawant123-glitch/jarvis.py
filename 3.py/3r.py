import sys
import speech_recognition as sr
import pyttsx3
import wikipedia
import webbrowser
import datetime
import os
import cv2
import psutil
import pywhatkit as kit
import time
import pyautogui
import random
import subprocess
import platform
import socket
import clipboard
import json
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from PIL import Image
from flask import Flask, request, jsonify, render_template_string
import threading
from pathlib import Path
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='.', template_folder='.')
DB_PATH = Path(os.environ.get("JARVIS_DB_PATH", Path(__file__).with_name("jarvis_data.sqlite3")))
state_lock = threading.RLock()
speech_lock = threading.Lock()
offline_model_lock = threading.Lock()
offline_model_cache = {"path": None, "model": None}
assistant_state = {"active": False, "listening": False, "error": None}
reminder_timers = []

# Fix Encoding Error
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

engine = pyttsx3.init()

# Pre-defined Voice Password
VOICE_PASSWORD = "open jarvis"
WAKE_WORD = "jarvis"
chatbot_responses = {
    "hello": "Hello Sir! How can I help you?",
    "how are you": "I'm just a virtual assistant, but I'm doing great! How can I assist you?",
    "who are you": "I am Jarvis, your personal AI assistant.",
    "thank you": "You're welcome Sir!"
}


@contextmanager
def connect_db():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database():
    with connect_db() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                source TEXT NOT NULL,
                command TEXT NOT NULL,
                response TEXT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                due_at TEXT,
                completed INTEGER NOT NULL DEFAULT 0,
                kind TEXT NOT NULL DEFAULT 'task',
                created_at TEXT NOT NULL
            );
        """)
        defaults = {
            "wake_word": "jarvis",
            "speech_rate": "150",
            "voice_id": "",
            "city": "London",
            "offline_mode": "false",
            "offline_model_path": str(Path(__file__).with_name("models") / "vosk-model-small-en-us-0.15"),
        }
        connection.executemany(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            defaults.items(),
        )


initialize_database()


def get_settings():
    with connect_db() as connection:
        return {row["key"]: row["value"] for row in connection.execute("SELECT key, value FROM settings")}


def update_setting(key, value):
    with connect_db() as connection:
        connection.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )


def add_history(command, response, status="ok", source="voice"):
    with connect_db() as connection:
        connection.execute(
            "INSERT INTO history (created_at, source, command, response, status) VALUES (?, ?, ?, ?, ?)",
            (datetime.now().astimezone().isoformat(timespec="seconds"), source, command, response, status),
        )


def set_assistant_state(**changes):
    with state_lock:
        assistant_state.update(changes)


# Speak Function
def speak(text):
    settings = get_settings()
    with speech_lock:
        engine.setProperty("rate", int(settings["speech_rate"]))
        voices = engine.getProperty("voices")
        voice_id = settings["voice_id"] or (voices[0].id if voices else "")
        if voice_id:
            engine.setProperty("voice", voice_id)
        engine.say(text)
        engine.runAndWait()

# Welcome Sound
def welcome():
    speak("Welcome back Sir! How can I assist you?")

# Voice Password
def voice_password():
    speak("Please say the password to proceed")
    password = listen(record=False)
    if password == VOICE_PASSWORD:
        speak("Access Granted")
        return True
    else:
        speak("Access Denied")
        return False

# Face Recognition
def face_login():
    cam = cv2.VideoCapture(0)
    try:
        result, image = cam.read()
        if result:
            cv2.imshow("Face Recognition", image)
            cv2.imwrite("face.jpg", image)
            cv2.waitKey(2000)
            cv2.destroyAllWindows()
            speak("Face Recognized Successfully")
            return
        message = "Camera unavailable. Connect a camera or check camera permissions."
        set_assistant_state(error=message)
        speak(message)
    except cv2.error as error:
        message = f"Camera error: {error}"
        set_assistant_state(error=message)
        speak(message)
    finally:
        cam.release()
        cv2.destroyAllWindows()

# Listen Function
def listen(record=True):
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            set_assistant_state(listening=True)
            print("🎙️ Listening...")
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=12)
        settings = get_settings()
        if settings["offline_mode"].lower() == "true":
            model_path = Path(settings["offline_model_path"]).expanduser()
            if not model_path.is_dir():
                raise RuntimeError(
                    f"Offline speech model not found at {model_path}. Install Vosk and add a model folder."
                )
            try:
                vosk = __import__("vosk")
            except ImportError as error:
                raise RuntimeError("Offline speech recognition requires Vosk. Install it with: pip install vosk") from error
            with offline_model_lock:
                if offline_model_cache["path"] != str(model_path):
                    offline_model_cache.update(path=str(model_path), model=vosk.Model(str(model_path)))
                model = offline_model_cache["model"]
            audio_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
            decoder = vosk.KaldiRecognizer(model, 16000)
            decoder.AcceptWaveform(audio_data)
            query = json.loads(decoder.FinalResult()).get("text", "").strip()
        else:
            query = recognizer.recognize_google(audio)
        if query:
            query = query.lower()
            print(f"You said: {query}")
            set_assistant_state(error=None)
            if record:
                add_history(query, "Heard voice input", source="voice")
            return query
        return None
    except sr.WaitTimeoutError:
        return None
    except sr.RequestError as error:
        message = "Online speech recognition is unavailable. Enable offline mode and configure a Vosk model to continue."
        set_assistant_state(error=message)
        print(f"Speech recognition error: {error}")
        raise RuntimeError(message) from error
    except AttributeError as error:
        message = f"Microphone unavailable: {error}. Check your microphone and audio input installation."
        set_assistant_state(error=message)
        print(message)
        raise RuntimeError(message) from error
    except (OSError, RuntimeError, ImportError) as error:
        message = f"Microphone or speech recognition error: {error}"
        set_assistant_state(error=message)
        print(message)
        raise RuntimeError(message) from error
    except sr.UnknownValueError:
        return None
    finally:
        set_assistant_state(listening=False)

def wait_for_wake_word():
    while True:
        print("👂 Waiting for wake word...")
        query = listen()
        wake_word = get_settings()["wake_word"].lower()
        if query and wake_word in query:
            speak("Yes sir, I am listening")
            return

# Network Speed
def network_speed():
    interfaces = psutil.net_if_stats()
    for name, stats in interfaces.items():
        if stats.isup:
            speak(f"Your current network interface is {name} with speed {stats.speed} Mbps")
            return
    speak("No active network connection found.")

# Bluetooth On/Off
def bluetooth_on_off(state):
    command = "Start-Service bthserv" if state == "on" else "Stop-Service bthserv"
    os.system(f"powershell.exe {command}")
    speak(f"Bluetooth Turned {state.capitalize()}")

# WhatsApp Message
def whatsapp_message(number, message):
    kit.sendwhatmsg_instantly(number, message)
    speak("Message Sent Successfully")

# Scroll Window
def scroll_window(direction):
    pyautogui.scroll(300 if direction == "up" else -300)
    speak(f"Scrolling {direction.capitalize()}")

# YouTube Search
def youtube_search(query):
    if query:
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        webbrowser.open(url)
        speak(f"Searching {query} on YouTube")

# YouTube Voice Search
def youtube_voice_search():
    speak("What do you want to search on YouTube?")
    query = listen()
    youtube_search(query)

# Open New Tab
def open_new_tab():
    pyautogui.hotkey("ctrl", "t")
    speak("Opening New Tab")

# Close Tab
def close_tab():
    pyautogui.hotkey("ctrl", "w")
    speak("Closing Tab")

# Previous Tab
def previous_tab():
    pyautogui.hotkey("ctrl", "shift", "tab")
    speak("Going to Previous Tab")

# Tell a Joke
def tell_joke():
    jokes = [
        "Why did the computer go to the doctor? Because it had a virus!",
        "Why do programmers prefer dark mode? Because light attracts bugs!"
    ]
    speak(random.choice(jokes))

# Battery Status
def battery_status():
    battery = psutil.sensors_battery()
    speak(f"Battery is at {battery.percent} percent")

# Take Screenshot
def take_screenshot():
    path = os.path.join(os.getcwd(), f"screenshot_{int(time.time())}.png")
    pyautogui.screenshot(path)
    speak("Screenshot taken")

# Get IP Address
def get_ip():
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    speak(f"Your IP address is {ip}")

# Get Clipboard Content
def get_clipboard():
    text = clipboard.paste()
    speak(f"Clipboard says: {text}")

# Code Calculator
def code_calculator():
    speak("Say the calculation")
    expr = listen()
    try:
        result = eval(expr)
        speak(f"The answer is {result}")
    except:
        speak("Sorry, I couldn't calculate that")

# Open Application
def open_app(name):
    try:
        os.system(f'start {name}')
        speak(f"Opening {name}")
    except:
        speak("App not found")

# Shutdown Computer
def shutdown():
    speak("Shutting down")
    os.system("shutdown /s /t 1")

# Reminder
def reminder():
    speak("What should I remind you?")
    task = listen()
    speak("In how many seconds?")
    seconds = listen()
    try:
        seconds = int(seconds)
        schedule_reminder(task, seconds)
    except (TypeError, ValueError):
        speak("I couldn't understand the reminder time.")


def schedule_reminder(task, seconds):
    if not task or seconds <= 0:
        raise ValueError("A reminder needs a message and a positive delay.")
    due_at = datetime.now().astimezone() + timedelta(seconds=seconds)
    with connect_db() as connection:
        connection.execute(
            "INSERT INTO tasks (title, due_at, kind, created_at) VALUES (?, ?, 'reminder', ?)",
            (task, due_at.isoformat(timespec="seconds"), datetime.now().astimezone().isoformat(timespec="seconds")),
        )

    def notify():
        message = f"Reminder: {task}"
        try:
            speak(message)
            add_history("reminder", message, source="reminder")
        except (RuntimeError, OSError) as error:
            set_assistant_state(error=f"Reminder is due but speech output failed: {error}")

    timer = threading.Timer(seconds, notify)
    timer.daemon = True
    reminder_timers.append(timer)
    timer.start()
    return f"Reminder set for {task} in {seconds} seconds."


def fetch_json(url):
    request_obj = urllib.request.Request(url, headers={"User-Agent": "JARVIS Assistant/1.0"})
    with urllib.request.urlopen(request_obj, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def get_weather(city):
    query = urllib.parse.urlencode({"name": city, "count": 1, "language": "en", "format": "json"})
    locations = fetch_json(f"https://geocoding-api.open-meteo.com/v1/search?{query}").get("results", [])
    if not locations:
        raise ValueError(f"Couldn't find a weather location named {city}.")
    location = locations[0]
    query = urllib.parse.urlencode({
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code",
    })
    weather = fetch_json(f"https://api.open-meteo.com/v1/forecast?{query}")["current"]
    return {
        "city": location["name"],
        "country": location.get("country", ""),
        "temperature": weather["temperature_2m"],
        "feels_like": weather["apparent_temperature"],
        "humidity": weather["relative_humidity_2m"],
        "condition": weather_condition(weather["weather_code"]),
    }


def weather_condition(code):
    if code == 0:
        return "Clear"
    if code in (1, 2, 3):
        return "Partly cloudy"
    if code in (45, 48):
        return "Fog"
    if code in (51, 53, 55, 56, 57):
        return "Drizzle"
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "Rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "Snow"
    if code in (95, 96, 99):
        return "Thunderstorm"
    return "Unknown conditions"


def get_news():
    request_obj = urllib.request.Request(
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        headers={"User-Agent": "JARVIS Assistant/1.0"},
    )
    with urllib.request.urlopen(request_obj, timeout=8) as response:
        root = ET.fromstring(response.read())
    return [
        {"title": item.findtext("title", default=""), "link": item.findtext("link", default="")}
        for item in root.findall("./channel/item")[:8]
    ]


def list_tasks(kind=None):
    with connect_db() as connection:
        if kind:
            rows = connection.execute(
                "SELECT id, title, due_at, completed, kind FROM tasks WHERE kind = ? ORDER BY completed, due_at, id",
                (kind,),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT id, title, due_at, completed, kind FROM tasks WHERE kind IN ('task', 'event') "
                "ORDER BY completed, due_at, id"
            ).fetchall()
    return [dict(row) for row in rows]


def handle_feature_command(query):
    lower = query.lower().strip()
    try:
        if re.search(r"\b(weather|forecast)\b", lower):
            city_match = re.search(r"\b(?:in|for)\s+(.+)$", lower)
            city = city_match.group(1).strip() if city_match else get_settings()["city"]
            weather = get_weather(city)
            response = (
                f"It's {weather['condition']} in {weather['city']}: {weather['temperature']} degrees, "
                f"feels like {weather['feels_like']}."
            )
            speak(response)
            return response
        if re.search(r"\b(news|headlines)\b", lower):
            headlines = get_news()
            response = "Here are the latest headlines: " + "; ".join(item["title"] for item in headlines[:3])
            speak(response)
            return response
        reminder_match = re.search(
            r"\bremind me in\s+(\d+)\s*(seconds?|minutes?|hours?)\s+(?:to\s+)?(.+)",
            lower,
        )
        if reminder_match:
            amount = int(reminder_match.group(1))
            unit = reminder_match.group(2)
            seconds = amount * (3600 if unit.startswith("hour") else 60 if unit.startswith("minute") else 1)
            response = schedule_reminder(reminder_match.group(3).strip(), seconds)
            speak(response)
            return response
        if "reminder" in lower:
            reminder()
            return "Reminder scheduled."
        if re.search(r"\b(add|create|schedule)\s+(?:a\s+)?(?:calendar\s+)?event\b", lower):
            title = re.sub(r"^.*?\b(?:event|calendar event)\b\s*(?:called|for|to)?\s*", "", lower).strip()
            if not title:
                title = re.sub(r"^.*?\b(?:add|create|schedule)\b\s*", "", lower).strip()
            if not title:
                return "Please include an event name."
            with connect_db() as connection:
                connection.execute(
                    "INSERT INTO tasks (title, kind, created_at) VALUES (?, 'event', ?)",
                    (title, datetime.now().astimezone().isoformat(timespec="seconds")),
                )
            response = f"Added calendar event: {title}."
            speak(response)
            return response
        if re.search(r"\b(add|create)\s+(?:a\s+)?(?:to-?do|task)\b", lower):
            title = re.sub(r"^.*?\b(?:to-?do|task)\b\s*(?:called|for|to)?\s*", "", lower).strip()
            if not title:
                return "Please include a task name."
            with connect_db() as connection:
                connection.execute(
                    "INSERT INTO tasks (title, kind, created_at) VALUES (?, 'task', ?)",
                    (title, datetime.now().astimezone().isoformat(timespec="seconds")),
                )
            response = f"Added task: {title}."
            speak(response)
            return response
        if re.search(r"\b(list|show)\s+(?:my\s+)?(?:tasks|to-?dos|calendar|events)\b", lower):
            kind = "event" if "calendar" in lower or "event" in lower else "task"
            items = list_tasks(kind)
            response = "You have no items." if not items else "; ".join(
                f"{item['title']}{' (completed)' if item['completed'] else ''}" for item in items
            )
            speak(response)
            return response
        complete_match = re.search(r"\b(?:complete|finish|done with)\s+(?:task\s+)?(.+)", lower)
        if complete_match:
            title = complete_match.group(1).strip()
            with connect_db() as connection:
                cursor = connection.execute(
                    "UPDATE tasks SET completed = 1 WHERE id = ? OR lower(title) = lower(?)",
                    (int(title) if title.isdigit() else -1, title),
                )
            response = f"Completed {title}." if cursor.rowcount else f"I couldn't find an open task named {title}."
            speak(response)
            return response
        if re.search(r"\b(play|pause|next track|skip track|volume up|volume down)\b", lower):
            action = "playpause" if "play" in lower or "pause" in lower else "nexttrack" if "next" in lower or "skip" in lower else "volumeup" if "up" in lower else "volumedown"
            pyautogui.press(action)
            response = f"Music control: {action.replace('track', ' track')}."
            speak(response)
            return response
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, OSError) as error:
        response = f"That service or device is unavailable: {error}"
        speak(response)
        return response
    return None


def get_voice_options():
    return [{"id": voice.id, "name": voice.name} for voice in engine.getProperty("voices")]

# Play Guessing Game
def play_guessing_game():
    speak("Let's play a number guessing game. Guess a number between 1 and 10")
    number = random.randint(1, 10)
    guess = listen()
    try:
        if int(guess) == number:
            speak("Congratulations! You guessed right.")
        else:
            speak(f"Sorry, the correct number was {number}")
    except:
        speak("That was not a number")

# Chatbot Response
def chatbot(query):
    for key in chatbot_responses:
        if key in query:
            speak(chatbot_responses[key])
            return
    speak("Sorry, I couldn't find an answer to that question!")

# Generate Text
def generate_text(prompt):
    responses = [
        f"Here's a paragraph on {prompt}...",
        f"Writing a letter about {prompt}...",
        f"Generating story on {prompt}..."
    ]
    speak(random.choice(responses))

# Run Python Script
def run_script():
    scripts = [f for f in os.listdir() if f.endswith(".py") and f != os.path.basename(__file__)]
    if scripts:
        speak("Running the first script I found")
        os.system(f"python {scripts[0]}")
    else:
        speak("No Python script found")

# Wikipedia Summary
def wikipedia_summary():
    speak("What topic should I look up?")
    topic = listen()
    if topic:
        try:
            summary = wikipedia.summary(topic, sentences=2)
            speak(summary)
        except:
            speak("Couldn't find anything")

# Convert JPG to PNG
def convert_jpg_to_png(image_path):
    try:
        img = Image.open(image_path)
        new_path = image_path.replace(".jpg", ".png")
        img.save(new_path, "PNG")
        return new_path
    except:
        return image_path

# Main JARVIS Function
def jarvis():
    welcome()
    if not voice_password():
        set_assistant_state(error="Voice password was not accepted.")
        return
    face_login()
    while True:
        query = listen()
        if query:
            wake_word = get_settings()["wake_word"].lower()
            if wake_word in query:
                query = query.replace(wake_word, "", 1).strip() or query
            feature_response = handle_feature_command(query)
            if feature_response is not None:
                status = "error" if feature_response.startswith("That service or device is unavailable:") else "ok"
                add_history(query, feature_response, status=status, source="voice")
                continue
            if "exit" in query or "bye" in query:
                speak("Goodbye Sir! Have a nice day.")
                break
            elif "open youtube" in query:
                webbrowser.open("https://www.youtube.com")
            elif "search youtube" in query:
                youtube_voice_search()
            elif "new tab" in query:
                open_new_tab()
            elif "close tab" in query:
                close_tab()
            elif "previous tab" in query:
                previous_tab()
            elif "scroll up" in query:
                scroll_window("up")
            elif "scroll down" in query:
                scroll_window("down")
            elif "time" in query:
                speak(datetime.datetime.now().strftime("%H:%M:%S"))
            elif "network speed" in query:
                network_speed()
            elif "bluetooth on" in query:
                bluetooth_on_off("on")
            elif "bluetooth off" in query:
                bluetooth_on_off("off")
            elif "send whatsapp message" in query:
                speak("Tell the number")
                number = listen()
                speak("Your message")
                message = listen()
                whatsapp_message(number, message)
            elif "joke" in query:
                tell_joke()
            elif "battery" in query:
                battery_status()
            elif "screenshot" in query:
                take_screenshot()
            elif "ip address" in query:
                get_ip()
            elif "clipboard" in query:
                get_clipboard()
            elif "calculate" in query:
                code_calculator()
            elif "shutdown" in query:
                shutdown()
            elif "play game" in query:
                play_guessing_game()
            elif "run script" in query:
                run_script()
            elif "search wikipedia" in query:
                wikipedia_summary()
            elif "generate text" in query:
                speak("What topic?")
                topic = listen()
                generate_text(topic)
            elif "open app" in query:
                speak("App name?")
                open_app(listen())
            else:
                chatbot(query)


def run_assistant():
    set_assistant_state(active=True, listening=False, error=None)
    try:
        jarvis()
    except (OSError, RuntimeError, sr.Microphone, cv2.error) as error:
        message = f"JARVIS stopped: {error}"
        set_assistant_state(error=message)
        add_history("assistant", message, status="error", source="system")
        print(message)
    finally:
        set_assistant_state(active=False, listening=False)

@app.route('/')
def index():
    page = Path(__file__).with_name("main.html").read_text(encoding="utf-8")
    return render_template_string(page)

@app.route('/start_jarvis', methods=['POST'])
def start_jarvis_route():
    with state_lock:
        if assistant_state["active"]:
            return jsonify({'status': 'JARVIS is already running.'})
        assistant_state.update(active=True, listening=False, error=None)
        worker = threading.Thread(target=run_assistant, daemon=True)
        worker.start()
    return jsonify({'status': 'JARVIS is starting.'})


@app.route('/api/status')
def status_route():
    with state_lock:
        status = dict(assistant_state)
    return jsonify(status)


@app.route('/api/history')
def history_route():
    with connect_db() as connection:
        rows = connection.execute(
            "SELECT id, created_at, source, command, response, status FROM history ORDER BY id DESC LIMIT 30"
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.route('/api/command', methods=['POST'])
def command_route():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Command payload must be a JSON object."}), 400
    text = data.get("text", "")
    if not isinstance(text, str) or not text.strip():
        return jsonify({"error": "Enter a command first."}), 400
    text = text.strip()
    response = handle_feature_command(text)
    if response is None:
        response = "I don't recognize that command. Try weather, news, a reminder, a task, an event, or music controls."
        speak(response)
    status = "error" if response.startswith("That service or device is unavailable:") else "ok"
    add_history(text, response, status=status, source="web")
    return jsonify({"status": "ok", "response": response})


@app.route('/api/settings', methods=['GET', 'POST'])
def settings_route():
    if request.method == 'GET':
        settings = get_settings()
        settings["voices"] = get_voice_options()
        return jsonify(settings)
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Settings payload must be a JSON object."}), 400
    wake_word = str(data.get("wake_word", "")).strip()
    city = str(data.get("city", "")).strip()
    try:
        speech_rate = int(data.get("speech_rate", 150))
    except (TypeError, ValueError):
        return jsonify({"error": "Speech speed must be a number."}), 400
    if not wake_word or len(wake_word) > 40:
        return jsonify({"error": "Wake word must be between 1 and 40 characters."}), 400
    if not city or len(city) > 100:
        return jsonify({"error": "Enter a city name up to 100 characters."}), 400
    if not 80 <= speech_rate <= 300:
        return jsonify({"error": "Speech speed must be between 80 and 300."}), 400
    voice_id = str(data.get("voice_id", ""))
    valid_voice_ids = {voice["id"] for voice in get_voice_options()}
    if voice_id and voice_id not in valid_voice_ids:
        return jsonify({"error": "Select an available system voice."}), 400
    offline_mode = data.get("offline_mode", False)
    if not isinstance(offline_mode, bool):
        return jsonify({"error": "Offline mode must be enabled or disabled."}), 400
    model_path = str(data.get("offline_model_path", "")).strip()
    update_setting("wake_word", wake_word)
    update_setting("city", city)
    update_setting("speech_rate", speech_rate)
    update_setting("voice_id", voice_id)
    update_setting("offline_mode", str(offline_mode).lower())
    if model_path:
        update_setting("offline_model_path", model_path)
    return jsonify({"status": "Settings saved."})


@app.route('/api/tasks', methods=['GET', 'POST'])
def tasks_route():
    if request.method == 'GET':
        return jsonify(list_tasks())
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Task payload must be a JSON object."}), 400
    raw_title = data.get("title", "")
    if not isinstance(raw_title, str):
        return jsonify({"error": "Enter a valid task or event name."}), 400
    title = raw_title.strip()
    kind = data.get("kind", "task")
    if not title:
        return jsonify({"error": "Enter a task or event name."}), 400
    if kind not in ("task", "event"):
        return jsonify({"error": "Item type must be task or event."}), 400
    due_at = str(data.get("due_at", "")).strip() or None
    if due_at:
        try:
            due_at = datetime.fromisoformat(due_at.replace("Z", "+00:00")).isoformat(timespec="seconds")
        except ValueError:
            return jsonify({"error": "Enter a valid event date and time."}), 400
    with connect_db() as connection:
        cursor = connection.execute(
            "INSERT INTO tasks (title, due_at, kind, created_at) VALUES (?, ?, ?, ?)",
            (title, due_at, kind, datetime.now().astimezone().isoformat(timespec="seconds")),
        )
    return jsonify({"id": cursor.lastrowid, "title": title, "kind": kind}), 201


@app.route('/api/tasks/<int:task_id>', methods=['PATCH', 'DELETE'])
def task_item_route(task_id):
    with connect_db() as connection:
        if request.method == 'DELETE':
            cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        else:
            cursor = connection.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
    if not cursor.rowcount:
        return jsonify({"error": "Task or event not found."}), 404
    return jsonify({"status": "Task completed." if request.method == 'PATCH' else "Item deleted."})


@app.route('/api/weather')
def weather_route():
    city = request.args.get("city", "").strip() or get_settings()["city"]
    try:
        return jsonify(get_weather(city))
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as error:
        return jsonify({"error": f"Weather service unavailable: {error}"}), 503


@app.route('/api/news')
def news_route():
    try:
        return jsonify(get_news())
    except (urllib.error.URLError, TimeoutError, ET.ParseError) as error:
        return jsonify({"error": f"News service unavailable: {error}"}), 503

if __name__ == "__main__":
    import webbrowser
    threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:5000/")).start()
    app.run(debug=False, use_reloader=False)
"""
Legacy entry point — kept so old run instructions still work.

Prefer:  python app.py
Also OK: python 3r.py
"""

from app import main

if __name__ == "__main__":
    main()
