from flask import Flask, request, send_file, abort
import os
import pyperclip
from win10toast_click import ToastNotifier
import threading
import pystray
from PIL import Image
import pymsgbox
import tkinter as tk
from tkinter import filedialog
import socket
import smtplib
from email.mime.text import MIMEText
import keyboard
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

ICON_PATH = os.path.join(os.path.dirname(__file__), "icon.ico")
notifier = ToastNotifier()

share_file_path = None
port = 5000
require_confirmation = False


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't have to be reachable
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return f'http://{ip}:{port}'
def mail(body):
    def send_mail(body):
        user = os.getenv("AIRMAIL_USER")
        pwd = os.getenv("AIRMAIL_PWD")
        to_email = os.getenv("AIRMAIL_TO")
        msg = MIMEText(body)
        msg["Subject"] = "Airdrop"
        msg["From"] = user
        msg["To"] = to_email
        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(user, pwd)
                server.send_message(msg)
        except Exception as e:
            print(f"Error: {e}")
    threading.Thread(target=send_mail, args=(body,), daemon=True).start()


# Helper to send Windows toast notifications
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
        path = os.path.abspath(filename)
        file.save(path)
        share_file_path = path
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


def select_file_to_share():
    def open_file_dialog():
        global share_file_path
        root = tk.Tk()
        root.withdraw()
        try:
            path = filedialog.askopenfilename(title="Select file to share", parent=root)
            if path:
                share_file_path = path
                mail('D$&@')
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
        pystray.MenuItem("Quit", lambda icon, item: icon.stop()),
    )
    tray = pystray.Icon("Airdrop_server", img, "Airdrop_server", menu)
    tray.run()

def send_clipboard():
    text = pyperclip.paste()
    if text.strip():
        mail(text)
        notify("Sent clipboard content via mail.")
    else:
        notify("Clipboard is empty.")

keyboard.add_hotkey('ctrl+alt+s', send_clipboard)

# Start Flask server in background
def run_server():
    mail(get_local_ip())
    app.run(host="0.0.0.0", port=port)


threading.Thread(target=run_server, daemon=True).start()
# Launch tray icon (blocks)
start_tray()

