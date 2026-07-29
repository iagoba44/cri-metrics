import os
import json

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config_settings.json")

DEFAULT_SETTINGS = {
    "alert_threshold": 65.0,
    "channels": {
        "slack": {"enabled": False, "url": ""},
        "discord": {"enabled": False, "url": ""},
        "telegram": {"enabled": False, "bot_token": "", "chat_id": ""},
        "email": {
            "enabled": False,
            "smtp_server": "",
            "smtp_port": 587,
            "username": "",
            "password": "",
            "to_email": ""
        }
    }
}

def load_settings() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_SETTINGS

def save_settings(settings: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Error saving settings: {e}")
