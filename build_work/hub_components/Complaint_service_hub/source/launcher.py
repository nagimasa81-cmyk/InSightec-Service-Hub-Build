"""Distribution-only launcher for InSightec Complaint Service Hub.

The packaged launcher NEVER falls back to a Python source file. This prevents a
standalone build from accidentally invoking the user's system Python, where
PySide6 or other packaged dependencies may not be installed.
"""
from __future__ import annotations

import ctypes
import datetime
import os
import subprocess
import sys
import traceback
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PENDING = APP_DIR / "updates" / "pending_program_update.zip"
LOG = APP_DIR / "logs" / "launcher.log"
HUB_EXE = APP_DIR / "Complaint_Service_Hub.exe"
UPDATER_EXE = APP_DIR / "Complaint_Service_Hub_Updater.exe"


def log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {message}\n")


def show_error(title: str, message: str) -> None:
    log(f"ERROR DIALOG: {title}: {message}")
    if os.name == "nt":
        try:
            ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
            return
        except Exception:
            pass
    print(f"{title}: {message}", file=sys.stderr)


def require_executable(path: Path, role: str) -> Path:
    if path.is_file():
        return path
    raise FileNotFoundError(
        f"{role} executable is missing:\n{path}\n\n"
        "Do not run a file copied out of the distribution folder. "
        "Extract the complete artifact and keep all files together."
    )


def run_pending_update() -> None:
    if not PENDING.is_file():
        return
    updater = require_executable(UPDATER_EXE, "Updater")
    command = [str(updater), str(PENDING)]
    log("Pending update command: " + " | ".join(command))
    result = subprocess.run(command, cwd=str(APP_DIR), check=False)
    log(f"Updater returned {result.returncode}")
    if result.returncode != 0:
        raise RuntimeError(f"Program Update failed with exit code {result.returncode}.")


def start_hub() -> None:
    hub = require_executable(HUB_EXE, "Hub")
    command = [str(hub)]
    log("Hub command: " + " | ".join(command))
    process = subprocess.Popen(command, cwd=str(APP_DIR))
    log(f"Hub process started. pid={process.pid}")

    try:
        return_code = process.wait(timeout=3.0)
    except subprocess.TimeoutExpired:
        log("Hub remained active after startup grace period.")
        return

    if return_code != 0:
        raise RuntimeError(
            f"The Hub closed during startup with exit code {return_code}.\n\n"
            f"Check:\n{LOG}\nand\n{APP_DIR / 'logs' / 'hub_startup_error.log'}"
        )
    log("Hub exited normally during startup grace period.")


def main() -> int:
    try:
        os.chdir(APP_DIR)
        log(
            "Launcher started. "
            f"launcher={sys.executable!r}, app_dir={str(APP_DIR)!r}, "
            f"hub_exists={HUB_EXE.is_file()}, updater_exists={UPDATER_EXE.is_file()}"
        )
        run_pending_update()
        start_hub()
        return 0
    except Exception as exc:
        detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        log(detail.rstrip())
        show_error(
            "Complaint Service Hub - Startup Error",
            "The application could not start.\n\n"
            f"{exc}\n\nDiagnostic log:\n{LOG}",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
