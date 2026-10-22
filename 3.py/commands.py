"""Command handlers shared by voice loop and text API."""

import datetime
import os
import random
import socket
import time
import webbrowser

import clipboard
import psutil
import pyautogui
import pywhatkit as kit
import wikipedia
from PIL import Image

from config import CHATBOT_RESPONSES
from speech import speak, listen_or_none


def _reply(message, speak_reply=True):
    if speak_reply and message:
        speak(message)
    return {"ok": True, "reply": message, "needs_input": False}


def _need_input(prompt, field):
    return {
        "ok": True,
        "reply": prompt,
        "needs_input": True,
        "field": field,
    }


def _fail(message, speak_reply=True):
    if speak_reply and message:
        speak(message)
    return {"ok": False, "reply": message, "needs_input": False}


def network_speed(speak_reply=True):
    try:
        interfaces = psutil.net_if_stats()
        for name, stats in interfaces.items():
            if stats.isup:
                return _reply(
                    f"Your current network interface is {name} with speed {stats.speed} Mbps",
                    speak_reply,
                )
        return _reply("No active network connection found.", speak_reply)
    except Exception as exc:
        return _fail(f"Could not read network status: {exc}", speak_reply)


def bluetooth_on_off(state, speak_reply=True):
    try:
        command = "Start-Service bthserv" if state == "on" else "Stop-Service bthserv"
        os.system(f"powershell.exe {command}")
        return _reply(f"Bluetooth turned {state}", speak_reply)
    except Exception as exc:
        return _fail(f"Bluetooth command failed: {exc}", speak_reply)


def whatsapp_message(number, message, speak_reply=True):
    try:
        kit.sendwhatmsg_instantly(number, message)
        return _reply("Message sent successfully", speak_reply)
    except Exception as exc:
        return _fail(f"Could not send WhatsApp message: {exc}", speak_reply)


def scroll_window(direction, speak_reply=True):
    try:
        pyautogui.scroll(300 if direction == "up" else -300)
        return _reply(f"Scrolling {direction}", speak_reply)
    except Exception as exc:
        return _fail(f"Scroll failed: {exc}", speak_reply)


def youtube_search(query, speak_reply=True):
    if not query:
        return _fail("No search query provided.", speak_reply)
    url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    webbrowser.open(url)
    return _reply(f"Searching {query} on YouTube", speak_reply)


def open_new_tab(speak_reply=True):
    pyautogui.hotkey("ctrl", "t")
    return _reply("Opening new tab", speak_reply)


def close_tab(speak_reply=True):
    pyautogui.hotkey("ctrl", "w")
    return _reply("Closing tab", speak_reply)


def previous_tab(speak_reply=True):
    pyautogui.hotkey("ctrl", "shift", "tab")
    return _reply("Going to previous tab", speak_reply)


def tell_joke(speak_reply=True):
    jokes = [
        "Why did the computer go to the doctor? Because it had a virus!",
        "Why do programmers prefer dark mode? Because light attracts bugs!",
    ]
    return _reply(random.choice(jokes), speak_reply)


def battery_status(speak_reply=True):
    try:
        battery = psutil.sensors_battery()
        if battery is None:
            return _reply("Battery information is not available on this device.", speak_reply)
        return _reply(f"Battery is at {battery.percent} percent", speak_reply)
    except Exception as exc:
        return _fail(f"Could not read battery: {exc}", speak_reply)


def take_screenshot(speak_reply=True):
    try:
        path = os.path.join(os.getcwd(), f"screenshot_{int(time.time())}.png")
        pyautogui.screenshot(path)
        return _reply(f"Screenshot saved as {os.path.basename(path)}", speak_reply)
    except Exception as exc:
        return _fail(f"Screenshot failed: {exc}", speak_reply)


def get_ip(speak_reply=True):
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return _reply(f"Your IP address is {ip}", speak_reply)
    except Exception as exc:
        return _fail(f"Could not get IP address: {exc}", speak_reply)


def get_clipboard(speak_reply=True):
    try:
        text = clipboard.paste()
        if not text:
            return _reply("Clipboard is empty.", speak_reply)
        return _reply(f"Clipboard says: {text}", speak_reply)
    except Exception as exc:
        return _fail(f"Could not read clipboard: {exc}", speak_reply)


def calculate(expr, speak_reply=True):
    if not expr:
        return _fail("No expression provided.", speak_reply)
    try:
        # Restrict eval to simple math
        allowed = {"__builtins__": {}}
        result = eval(expr, allowed, {})
        return _reply(f"The answer is {result}", speak_reply)
    except Exception:
        return _fail("Sorry, I could not calculate that.", speak_reply)


def open_app(name, speak_reply=True):
    if not name:
        return _fail("No app name provided.", speak_reply)
    try:
        os.system(f"start {name}")
        return _reply(f"Opening {name}", speak_reply)
    except Exception:
        return _fail("App not found", speak_reply)


def shutdown(speak_reply=True):
    speak("Shutting down") if speak_reply else None
    os.system("shutdown /s /t 1")
    return {"ok": True, "reply": "Shutting down", "needs_input": False}


def set_reminder(task, seconds, speak_reply=True):
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return _fail("Invalid time. Please give seconds as a number.", speak_reply)
    _reply(f"Reminder set for {task} in {seconds} seconds", speak_reply)
    time.sleep(seconds)
    return _reply(f"Reminder: {task}", speak_reply)


def play_guessing_game(guess=None, speak_reply=True, ask_fn=None):
    number = random.randint(1, 10)
    if guess is None and ask_fn:
        speak("Let's play a number guessing game. Guess a number between 1 and 10")
        guess = ask_fn()
    elif guess is None:
        return _need_input(
            "Guess a number between 1 and 10. Send again with field 'guess'.",
            "guess",
        )
    try:
        if int(guess) == number:
            return _reply("Congratulations! You guessed right.", speak_reply)
        return _reply(f"Sorry, the correct number was {number}", speak_reply)
    except (TypeError, ValueError):
        return _fail("That was not a number.", speak_reply)


def chatbot(query, speak_reply=True):
    for key, response in CHATBOT_RESPONSES.items():
        if key in query:
            return _reply(response, speak_reply)
    return _reply("Sorry, I could not find an answer to that question!", speak_reply)


def generate_text(prompt, speak_reply=True):
    if not prompt:
        return _fail("No topic provided.", speak_reply)
    responses = [
        f"Here's a paragraph on {prompt}...",
        f"Writing a letter about {prompt}...",
        f"Generating story on {prompt}...",
    ]
    return _reply(random.choice(responses), speak_reply)


def run_script(speak_reply=True):
    scripts = [
        f
        for f in os.listdir()
        if f.endswith(".py")
        and f
        not in {
            "app.py",
            "server.py",
            "3r.py",
            "config.py",
            "speech.py",
            "auth.py",
            "commands.py",
            "jarvis_core.py",
        }
    ]
    if scripts:
        os.system(f"python {scripts[0]}")
        return _reply(f"Running {scripts[0]}", speak_reply)
    return _reply("No Python script found", speak_reply)


def wikipedia_summary(topic, speak_reply=True):
    if not topic:
        return _fail("No topic provided.", speak_reply)
    try:
        summary = wikipedia.summary(topic, sentences=2)
        return _reply(summary, speak_reply)
    except wikipedia.exceptions.DisambiguationError as exc:
        options = ", ".join(exc.options[:5])
        return _fail(
            f"Topic is ambiguous. Try one of: {options}",
            speak_reply,
        )
    except wikipedia.exceptions.PageError:
        return _fail("Could not find that topic on Wikipedia.", speak_reply)
    except Exception:
        return _fail(
            "Wikipedia lookup failed. Check your internet connection.",
            speak_reply,
        )


def convert_jpg_to_png(image_path):
    try:
        img = Image.open(image_path)
        new_path = image_path.replace(".jpg", ".png")
        img.save(new_path, "PNG")
        return new_path
    except Exception:
        return image_path


def process_command(query, speak_reply=True, extras=None, ask_fn=None):
    """
    Run one user command.
    - query: full command text
    - speak_reply: speak aloud (voice mode) or silent (text API)
    - extras: optional dict for follow-up fields (topic, expression, guess, ...)
    - ask_fn: callable that returns next spoken input (voice mode)
    Returns dict: {ok, reply, needs_input?, field?}
    """
    extras = extras or {}
    if not query or not str(query).strip():
        return _fail("Empty command.", speak_reply)

    query = str(query).strip().lower()

    if "exit" in query or "bye" in query:
        return _reply("Goodbye Sir! Have a nice day.", speak_reply)

    if "open youtube" in query:
        webbrowser.open("https://www.youtube.com")
        return _reply("Opening YouTube", speak_reply)

    if "search youtube" in query:
        topic = extras.get("topic")
        if not topic and ask_fn:
            speak("What do you want to search on YouTube?")
            topic = ask_fn()
        if not topic:
            # allow "search youtube cats"
            rest = query.replace("search youtube", "").strip()
            topic = rest or None
        if not topic:
            return _need_input("What should I search on YouTube?", "topic")
        return youtube_search(topic, speak_reply)

    if "new tab" in query:
        return open_new_tab(speak_reply)
    if "close tab" in query:
        return close_tab(speak_reply)
    if "previous tab" in query:
        return previous_tab(speak_reply)
    if "scroll up" in query:
        return scroll_window("up", speak_reply)
    if "scroll down" in query:
        return scroll_window("down", speak_reply)

    if "time" in query:
        now = datetime.datetime.now().strftime("%H:%M:%S")
        return _reply(f"The time is {now}", speak_reply)

    if "network speed" in query:
        return network_speed(speak_reply)
    if "bluetooth on" in query:
        return bluetooth_on_off("on", speak_reply)
    if "bluetooth off" in query:
        return bluetooth_on_off("off", speak_reply)

    if "send whatsapp message" in query:
        number = extras.get("number")
        message = extras.get("message")
        if ask_fn:
            if not number:
                speak("Tell the number")
                number = ask_fn()
            if not message:
                speak("Your message")
                message = ask_fn()
        if not number or not message:
            return _need_input(
                "Provide 'number' and 'message' in the request body.",
                "number",
            )
        return whatsapp_message(number, message, speak_reply)

    if "joke" in query:
        return tell_joke(speak_reply)
    if "battery" in query:
        return battery_status(speak_reply)
    if "screenshot" in query:
        return take_screenshot(speak_reply)
    if "ip address" in query:
        return get_ip(speak_reply)
    if "clipboard" in query:
        return get_clipboard(speak_reply)

    if "calculate" in query:
        expr = extras.get("expression") or extras.get("expr")
        if not expr and ask_fn:
            speak("Say the calculation")
            expr = ask_fn()
        if not expr:
            expr = query.replace("calculate", "").strip()
        if not expr:
            return _need_input("Provide an expression, e.g. calculate 5 + 3", "expression")
        return calculate(expr, speak_reply)

    if "shutdown" in query:
        return shutdown(speak_reply)

    if "reminder" in query:
        task = extras.get("task")
        seconds = extras.get("seconds")
        if ask_fn:
            if not task:
                speak("What should I remind you?")
                task = ask_fn()
            if not seconds:
                speak("In how many seconds?")
                seconds = ask_fn()
        if not task or seconds is None:
            return _need_input(
                "Provide 'task' and 'seconds' in the request body.",
                "task",
            )
        return set_reminder(task, seconds, speak_reply)

    if "play game" in query:
        return play_guessing_game(
            guess=extras.get("guess"),
            speak_reply=speak_reply,
            ask_fn=ask_fn,
        )

    if "run script" in query:
        return run_script(speak_reply)

    if "search wikipedia" in query or "wikipedia" in query:
        topic = extras.get("topic")
        if not topic and ask_fn:
            speak("What topic should I look up?")
            topic = ask_fn()
        if not topic:
            topic = (
                query.replace("search wikipedia", "")
                .replace("wikipedia", "")
                .strip()
            )
        if not topic:
            return _need_input("What topic should I look up on Wikipedia?", "topic")
        return wikipedia_summary(topic, speak_reply)

    if "generate text" in query:
        topic = extras.get("topic")
        if not topic and ask_fn:
            speak("What topic?")
            topic = ask_fn()
        if not topic:
            topic = query.replace("generate text", "").strip()
        if not topic:
            return _need_input("What topic should I generate text about?", "topic")
        return generate_text(topic, speak_reply)

    if "open app" in query:
        name = extras.get("name") or extras.get("app")
        if not name and ask_fn:
            speak("App name?")
            name = ask_fn()
        if not name:
            name = query.replace("open app", "").strip()
        if not name:
            return _need_input("Which app should I open?", "name")
        return open_app(name, speak_reply)

    return chatbot(query, speak_reply)
