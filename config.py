import json
from pathlib import Path
from typing import Any, Dict

APP_DIR = Path(__file__).parent
CONFIG_FILE = APP_DIR / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "broadcast_ip": "192.168.252.255",
    "macro_target_ip": "192.168.252.50",
    "udp_port": 5000,
    "macro_udp_port": 52737,
    "wol_port": 9,
    "enable_wol_on_action": True,
    "wol_mac_addresses": [],
    "on_input": 0,
    "off_input": 1,
    "action_on_name": "EXHIBITION_ON",
    "action_off_name": "EXHIBITION_OFF",
    "broadcast_on_command": "INSTALL_ON",
    "broadcast_off_command": "INSTALL_OFF",
    "macro_on_command": "macro 1",
    "macro_off_command": "macro 9",
    "install_on_delay_seconds": 600.0,
    "macro_off_delay_seconds": 0.0,
    "enable_macro_off_message": True,
    "enable_udp_broadcast_target": True,
    "serial_number": 616656,
    "debounce_seconds": 0.15,
    "lock_seconds": 1.5,
    "send_repeats": 3,
    "send_interval_seconds": 0.25,
    "append_sequence": False,
    "log_enabled": True,
    "log_level": "INFO",
    "log_file": "phidget_controller.log",
    "status_file": "status.json",
    "reconnect_interval_seconds": 5,
    "max_reconnect_attempts": 0,
    "attach_timeout_ms": 5000,
    "press_on_state": True,
    "enable_test_hotkeys": True,
    "hotkey_on": "o",
    "hotkey_off": "f",
    "hotkey_broadcast_on": "b",
    "hotkey_macro_on": "1",
    "hotkey_macro_off": "9",
    "hotkey_quit": "q",
}


def load_config() -> Dict[str, Any]:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            merged = dict(DEFAULT_CONFIG)
            merged.update(loaded)
            return merged
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading config: {e}. Using defaults.")
        return dict(DEFAULT_CONFIG)


config = load_config()
