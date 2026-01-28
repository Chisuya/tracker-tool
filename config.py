"""
Configuration file for settings
"""

import json
import os

CONFIG_FILE = 'tracker_settings.json'

# Default settings
DEFAULT_SETTINGS = {
    'timezone': 'America/Los_Angeles'
}

def load_settings():
    """Load settings from file, or create default if doesn't exist"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Save settings to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

def get_timezone():
    """Get current timezone setting"""
    settings = load_settings()
    return settings.get('timezone', 'America/Los_Angeles')

def set_timezone(timezone):
    """Update timezone setting"""
    settings = load_settings()
    settings['timezone'] = timezone
    save_settings(settings)