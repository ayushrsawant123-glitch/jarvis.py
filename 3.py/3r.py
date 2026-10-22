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
from PIL import Image
from flask import Flask, request, jsonify, render_template_string
import threading

app = Flask(__name__, static_folder='.', template_folder='.')

# Fix Encoding Error
sys.stdout.reconfigure(encoding='utf-8')

engine = pyttsx3.init()
engine.setProperty("rate", 150)
engine.setProperty("voice", "english")

# Pre-defined Voice Password
VOICE_PASSWORD = "open jarvis"
WAKE_WORD = "jarvis"
chatbot_responses = {
    "hello": "Hello Sir! How can I help you?",
    "how are you": "I'm just a virtual assistant, but I'm doing great! How can I assist you?",
    "who are you": "I am Jarvis, your personal AI assistant.",
    "thank you": "You're welcome Sir!"
}

# Speak Function
def speak(text):
    engine.say(text)
    engine.runAndWait()

# Welcome Sound
def welcome():
    speak("Welcome back Sir! How can I assist you?")

# Voice Password
def voice_password():
    speak("Please say the password to proceed")
    password = listen()
    if password == VOICE_PASSWORD:
        speak("Access Granted")
        return True
    else:
        speak("Access Denied")
        return False

# Face Recognition
def face_login():
    cam = cv2.VideoCapture(0)
    result, image = cam.read()
    if result:
        cv2.imshow("Face Recognition", image)
        cv2.imwrite("face.jpg", image)
        cv2.waitKey(2000)
        cv2.destroyAllWindows()
        speak("Face Recognized Successfully")
    else:
        speak("Face Not Detected")

# Listen Function
def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎙️ Listening...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
        try:
            query = recognizer.recognize_google(audio)
            print(f"You said: {query}")
            return query.lower()
        except sr.UnknownValueError:
            speak("Sorry, I couldn't understand!")
            return None

def wait_for_wake_word():
    while True:
        print("👂 Waiting for wake word...")
        query = listen()
        if query and WAKE_WORD in query:
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
        speak(f"Reminder set for {task} in {seconds} seconds")
        time.sleep(seconds)
        speak(f"Reminder: {task}")
    except:
        speak("Invalid time")

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
    if voice_password():
        face_login()
        while True:
            query = listen()
            if query:
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
                elif "reminder" in query:
                    reminder()
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

@app.route('/')
def index():
    # Serve your main.html file
    with open("main.html", "r", encoding="utf-8") as f:
        return render_template_string(f.read())

@app.route('/start_jarvis', methods=['POST'])
def start_jarvis_route():
    threading.Thread(target=jarvis).start()
    return jsonify({'status': 'JARVIS started!'})

@app.route('/chat', methods=['POST'])
def chat_route():
    data = request.get_json(silent=True) or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'Enter a message first.'}), 400

    normalized_message = message.lower()
    reply = next(
        (response for keyword, response in chatbot_responses.items() if keyword in normalized_message),
        "I don't know that one yet. Try hello, how are you, who are you, or thank you.",
    )
    return jsonify({'reply': reply})

if __name__ == "__main__":
    import webbrowser
    threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:5000/")).start()
    app.run(debug=True)