from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

APP_FOLDER = "MR_Image_Explorer"


def runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def log_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / APP_FOLDER
    try:
        base.mkdir(parents=True, exist_ok=True)
        return base
    except Exception:
        return runtime_dir()


def write_failure(stage: str, exc: BaseException) -> Path:
    path = log_dir() / "startup_error.log"
    text = (
        f"Time: {datetime.now().isoformat(timespec='seconds')}\n"
        f"Stage: {stage}\n"
        f"Executable: {sys.executable}\n"
        f"Runtime directory: {runtime_dir()}\n"
        f"Working directory: {Path.cwd()}\n\n"
        + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    )
    try:
        path.write_text(text, encoding="utf-8")
    except Exception:
        pass
    return path


def show_native_error(exc: BaseException, path: Path) -> None:
    message = f"{type(exc).__name__}: {exc}\n\nLog:\n{path}"
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, "MR Image Explorer - Startup Error", 0x10)
    except Exception:
        print(message, file=sys.stderr)


def main() -> int:
    root = runtime_dir()
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    try:
        import app
    except BaseException as exc:
        path = write_failure("import app", exc)
        show_native_error(exc, path)
        return 1

    try:
        return int(app.main())
    except BaseException as exc:
        path = write_failure("app.main", exc)
        show_native_error(exc, path)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
