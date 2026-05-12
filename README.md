# Phidget Exhibition Controller

This project runs from `main.py`.

Code is split by responsibility:

- `inputs.py`: Phidget inputs, debounce, hotkeys, reconnect loop, and action timing.
- `udp.py`: UDP and Wake-on-LAN sending.
- `debug.py`: logging and status file writing.
- `actions.py`: action dispatch rules.
- `config.py`: config loading and defaults.
- `main.py`: signal handling and startup.

## Install

1. Install Python 3.10 or newer.
2. Open a terminal in this project folder.
3. (Optional) create and activate a virtual environment.
4. Install dependencies:

```powershell
pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

Hotkeys (configurable in `config.json`):

- `o`: exhibition ON action
- `f`: exhibition OFF action
- `b`: send macro ON + broadcast ON + WOL immediately
- `1`: send macro ON message directly
- `9`: send macro OFF message directly
- `q`: quit

Broadcast behavior:

- ON sends `macro 1` over UDP broadcast immediately.
- ON sends `INSTALL_ON` over UDP broadcast after `install_on_delay_seconds` (default 300s / 5 min).
- ON also sends Wake-on-LAN magic packets (when enabled) using the same subnet broadcast IP.
- OFF sends `INSTALL_OFF` over UDP broadcast.
- OFF optionally sends `macro 9` (controlled by `enable_macro_off_message`) after `macro_off_delay_seconds` (default `0.0`, effectively at the same time as `INSTALL_OFF`).
- Macro commands use `macro_target_ip` (default `192.168.252.50`) and `macro_udp_port` (default `52737`), while INSTALL commands use broadcast `udp_port`.
- Broadcast IP defaults to `192.168.252.255` (subnet broadcast).
- Only machines with your listener script running and handling these commands will react.

## Config Notes

`config.json` now supports a unified action model:

- `action_on_name` and `action_off_name`: logical exhibition actions.
- `on_input` and `off_input`: button channels.
- `hotkey_on` and `hotkey_off`: keyboard triggers for the same actions.
- `hotkey_broadcast_on`: keyboard trigger for immediate macro ON + broadcast ON + WOL.
- `hotkey_macro_on` and `hotkey_macro_off`: keyboard triggers for direct macro messages.
- `enable_udp_broadcast_target`: enable existing broadcast target.
- `broadcast_on_command` and `broadcast_off_command`: commands for broadcast hardware.
- `macro_on_command` and `macro_off_command`: extra UDP macro commands for ON/OFF flows.
- `macro_target_ip`: IP target for macro commands (default `192.168.252.50`).
- `macro_udp_port`: UDP port for macro commands (default `52737`).
- `install_on_delay_seconds`: delay before sending ON install command (default `300.0`).
- `macro_off_delay_seconds`: delay for OFF macro command (default `0.0`).
- `enable_macro_off_message`: enable/disable sending `macro 9` in OFF flow (default `true`).
- `enable_wol_on_action`: enable Wake-on-LAN packets on ON action.
- `wol_mac_addresses`: list of target MAC addresses for Wake-on-LAN.
- `wol_port`: Wake-on-LAN UDP port (default `9`).

This lets multiple hardware targets react to the same two actions without extra scripts.

## Troubleshooting

- `No output targets are enabled`: turn on at least one target in `config.json`.
- If OFF does not react on listeners, confirm they listen for `INSTALL_OFF` on UDP port `5000`.
