# Portable Deployment (Any Windows Machine)

This project is designed to run from its own folder with no hardcoded user paths.

## What is automated

`run_phidget.bat` now runs `scripts/setup_check.bat` before startup. The preflight checker will:

1. Create `phidget_venv` if missing.
2. Ensure `pip` exists in the venv and upgrade to `26.0.1`.
3. Install Python dependencies from `requirements.txt`.
4. Validate native `phidget22.dll` availability.
5. Start app only when checks pass.

A report is written to `preflight_report.txt` each run.

## One required native dependency

For this Phidget22-based controller, native runtime `phidget22.dll` is required.

You have three portable options:

1. Install Phidget22 runtime/driver package on the machine.
2. Place `phidget22.dll` in `drivers/phidget22/` inside this project folder.
3. Place `phidget22.dll` in the project root folder.

The preflight checker auto-detects these locations.

## Run

Double-click `run_phidget.bat`.

## Fast updates (no zip)

Use incremental sync with `scripts/deploy_sync.bat`.

Example:

`scripts\deploy_sync.bat "D:\Install\Phidget_controller"`

What it does:

1. Copies only changed/new files.
2. Uses multithreaded `robocopy` (`/MT:32`) for speed.
3. Skips heavy/local files like virtual environments and logs.

This is much faster than exporting and zipping each time.

## Windows Service (Auto Start on Boot)

Use NSSM for service installation:

1. Install NSSM and add it to `PATH`, or place `nssm.exe` in project root.
2. Run `scripts\install_service.bat` as Administrator.
3. To remove service later, run `scripts\uninstall_service.bat` as Administrator.

Service name: `PhidgetUdpController`

## First-time packaging for another PC

Copy this folder with at least:

- `main.py`
- `config.json`
- `run_phidget.bat`
- `scripts\setup_check.bat`
- `requirements.txt`
- optional: `drivers/phidget22/phidget22.dll`

This makes startup reproducible across machines.
