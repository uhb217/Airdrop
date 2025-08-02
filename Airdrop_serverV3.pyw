from flask import Flask, request, send_file, abort
import os
import pyperclip
from win10toast_click import ToastNotifier
import threading
import pystray
import requests
from PIL import Image
import pymsgbox
import tkinter as tk
from tkinter import filedialog
from zeroconf import ServiceInfo, Zeroconf
import socket
import keyboard
import time
import uuid

app = Flask(__name__)

ICON_PATH = os.path.join(os.path.dirname(__file__), "icon.ico")
notifier = ToastNotifier()

share_file_path = None
port = 5000
require_confirmation = False
DOWNLOAD = "D$&@"
IP = "IP$&@"
data = "null"

def trigger_pushcut_notification(DATA="null"):
    global data
    data = DATA
    url = "https://api.pushcut.io/E9THLwP-EaJiG__zhR_0c/notifications/Airdrop%F0%9F%9A%80"
    try:
        requests.post(url, verify=False)
    except Exception as e:
        print(f"Failed to send Pushcut notification: {e}")
def notify(message):
    notifier.show_toast(
        "Airdrop_server",
        message,
        icon_path=ICON_PATH if os.path.exists(ICON_PATH) else None,
        duration=5,
        threaded=True,
    )
def error_notify(message):
    notifier.show_toast(
        "Airdrop_server Error",
        message,
        icon_path=ICON_PATH if os.path.exists(ICON_PATH) else None,
        duration=5,
        threaded=True,
    )

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

def start_mdns_service():
    global zeroconf
    zeroconf = Zeroconf()

    hostname = socket.gethostname()
    ip = get_local_ip()

    service_info = ServiceInfo(
        "_http._tcp.local.",
        "airdrop._http._tcp.local.",
        addresses=[socket.inet_aton(ip)],
        port=port,
        properties={"version": "1.0"},
        server="airdrop.local.",
    )

    try:
        zeroconf.register_service(service_info)
        print(f"[mDNS] Service registered as airdrop.local on IP {ip}:{port}")
    except Exception as e:
        print(f"[mDNS] Failed to register mDNS service: {e}")


def on_exit(icon, item):
    try:
        zeroconf.unregister_all_services()
        zeroconf.close()
        print("[mDNS] Unregistered service.")
    except:
        pass
    icon.stop()

@app.route("/upload", methods=["POST"])
def upload():
    global share_file_path
    if "file" in request.files:
        file = request.files["file"]
        filename = file.filename
        if require_confirmation:
            confirm = pymsgbox.confirm(
                text=f"Airdrop_server wants to send you a file:\n\n{filename}\n\nAccept?",
                title="Airdrop_server",
                buttons=["Yes", "No"],
            )
            if confirm != "Yes":
                return "File rejected by user", 403
        UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        timestamp_str = str(int(time.time()))[7:]
        unique_id = uuid.uuid4().hex[:6]
        filename = f"image_{timestamp_str}_{unique_id}.png"
        path = os.path.join(UPLOAD_DIR, filename)
        file.save(path)
        notify(f"Received and set share path: {filename}")
        return f"Uploaded {filename}!"
    elif "text" in request.form:
        text = request.form["text"]
        if require_confirmation:
            preview = text[:100] + ("..." if len(text) > 100 else "")
            confirm = pymsgbox.confirm(
                text=f"Airdrop_server wants to send you this text:\n\n{preview}\n\nAccept?",
                title="Airdrop_server",
                buttons=["Yes", "No"],
            )
            if confirm != "Yes":
                return "Text rejected by user", 403
        pyperclip.copy(text)
        notify("Received text and copied to clipboard.")
        return "Text copied to clipboard!"
    return "No valid data provided", 400
@app.route("/download", methods=["GET"])
def download():
    if share_file_path and os.path.exists(share_file_path):
        return send_file(share_file_path, as_attachment=True)
    else:
        error_notify("No file available at the saved path.")
        return abort(404, description="No file available for download")
@app.route("/actionManager", methods=["GET"])
def action_manager():
    return data

def select_file_to_share():
    def open_file_dialog():
        global share_file_path
        root = tk.Tk()
        root.withdraw()
        try:
            path = filedialog.askopenfilename(title="Select file to share", parent=root)
            if path:
                share_file_path = path
                trigger_pushcut_notification(DOWNLOAD)
                notify(f"Share path set: {os.path.basename(path)}")
        except Exception as e:
            error_notify(f"Error selecting file: {e}")
        finally:
            root.destroy()

    threading.Thread(target=open_file_dialog, daemon=True).start()


# Toggle confirmation setting
def toggle_confirmation(icon, item):
    global require_confirmation
    require_confirmation = not require_confirmation
    status = "ON" if require_confirmation else "OFF"
    notify(f"Confirmation is now {status}")


# Build and run the system tray icon
def start_tray():
    img = (
        Image.open(ICON_PATH)
        if os.path.exists(ICON_PATH)
        else Image.new("RGB", (64, 64), color=(0, 0, 0))
    )
    menu = pystray.Menu(
        pystray.MenuItem(
            lambda item: "Require Confirmation: ON"
            if require_confirmation
            else "Require Confirmation: OFF",
            toggle_confirmation,
        ),
        pystray.MenuItem("Share File", lambda icon, item: select_file_to_share()),
        pystray.MenuItem("Quit",on_exit),
    )
    tray = pystray.Icon("Airdrop_server", img, "Airdrop_server", menu)
    tray.run()

def send_clipboard():
    text = pyperclip.paste()
    if text.strip():
        trigger_pushcut_notification(text)
        notify("Sent clipboard content via Pushcut.")
    else:
        notify("Clipboard is empty.")

keyboard.add_hotkey('ctrl+alt+s', send_clipboard)

# Start Flask server in background
def run_server():
    start_mdns_service()
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_server, daemon=True).start()
# Launch tray icon (blocks)
start_tray()

