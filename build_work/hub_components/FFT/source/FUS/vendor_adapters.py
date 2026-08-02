from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


CONFIG_NAME = "vendor_sdk_config.json"


@dataclass
class AdapterResult:
    vendor: str
    backend: str
    output_path: Path
    image: Optional[np.ndarray] = None
    kspace: Optional[np.ndarray] = None
    log: str = ""


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def config_path() -> Path:
    env = os.environ.get("MRI_VENDOR_SDK_CONFIG")
    return Path(env) if env else app_dir() / CONFIG_NAME


def load_config() -> dict:
    path = config_path()
    if not path.exists():
        return {"ge_orchestra": {}, "siemens_ice": {}, "siemens_twix": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(config: dict) -> None:
    config_path().write_text(json.dumps(config, indent=2), encoding="utf-8")


def _expand(value: str) -> str:
    return os.path.expandvars(os.path.expanduser(value or ""))


def backend_status() -> list[dict]:
    cfg = load_config()
    result = []
    for key, title in [
        ("ge_orchestra", "GE Orchestra SDK"),
        ("siemens_ice", "Siemens IDEA/ICE external recon"),
        ("siemens_twix", "Siemens TWIX Python fallback"),
    ]:
        item = cfg.get(key, {})
        exe = _expand(item.get("executable", ""))
        enabled = bool(item.get("enabled", False))
        if key == "siemens_twix":
            try:
                import twixtools  # noqa: F401
                available = True
                detail = "twixtools import available"
            except Exception as exc:
                available = False
                detail = f"twixtools unavailable: {exc}"
        else:
            available = bool(exe and Path(exe).exists())
            detail = exe or "Executable not configured"
        result.append({"key": key, "title": title, "enabled": enabled, "available": available, "detail": detail})
    return result


def _run_external(vendor: str, input_path: Path, output_dir: Path, item: dict) -> AdapterResult:
    exe = Path(_expand(item.get("executable", "")))
    if not exe.exists():
        raise FileNotFoundError(f"Configured executable does not exist: {exe}")
    template = item.get("arguments", '"{input}" "{output}"')
    values = {
        "input": str(input_path),
        "output": str(output_dir),
        "sdk_root": _expand(item.get("sdk_root", "")),
    }
    arg_string = template.format(**values)
    command = [str(exe)] + shlex.split(arg_string, posix=False)
    env = os.environ.copy()
    for key, value in item.get("environment", {}).items():
        env[str(key)] = _expand(str(value))
    proc = subprocess.run(command, capture_output=True, text=True, env=env, timeout=int(item.get("timeout_seconds", 900)))
    log = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    if proc.returncode != 0:
        raise RuntimeError(f"Vendor reconstruction failed with exit code {proc.returncode}.\n{log[-5000:]}")
    expected = item.get("result_file", "reconstruction.npz")
    result_path = output_dir / expected
    if not result_path.exists():
        candidates = list(output_dir.glob("*.npz")) + list(output_dir.glob("*.npy"))
        if not candidates:
            raise FileNotFoundError("Reconstruction completed but no NPZ/NPY result was found.")
        result_path = candidates[0]
    image, kspace = load_result(result_path)
    return AdapterResult(vendor=vendor, backend=exe.name, output_path=result_path, image=image, kspace=kspace, log=log)


def load_result(path: Path) -> tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    if path.suffix.lower() == ".npy":
        arr = np.load(path, allow_pickle=False)
        return (np.asarray(arr), None)
    data = np.load(path, allow_pickle=False)
    image = None
    kspace = None
    for key in ("image", "reconstruction", "magnitude", "rss_image"):
        if key in data:
            image = np.asarray(data[key])
            break
    for key in ("kspace", "raw", "data"):
        if key in data:
            kspace = np.asarray(data[key])
            break
    return image, kspace


def reconstruct_ge(input_path: Path, output_dir: Path) -> AdapterResult:
    cfg = load_config().get("ge_orchestra", {})
    if not cfg.get("enabled", False):
        raise RuntimeError("GE Orchestra adapter is disabled in vendor_sdk_config.json.")
    return _run_external("GE", input_path, output_dir, cfg)


def reconstruct_siemens_external(input_path: Path, output_dir: Path) -> AdapterResult:
    cfg = load_config().get("siemens_ice", {})
    if not cfg.get("enabled", False):
        raise RuntimeError("Siemens IDEA/ICE adapter is disabled in vendor_sdk_config.json.")
    return _run_external("Siemens", input_path, output_dir, cfg)


def reconstruct_siemens_twix(input_path: Path, output_dir: Path) -> AdapterResult:
    try:
        import twixtools
    except Exception as exc:
        raise RuntimeError("twixtools is not installed. Run 04_INSTALL_OPTIONAL_SIEMENS_TWIX.bat.") from exc

    measurements = twixtools.read_twix(str(input_path))
    if not measurements:
        raise RuntimeError("No measurement was found in the Siemens TWIX file.")
    mapped = twixtools.map_twix(measurements[-1])
    if "image" not in mapped:
        raise RuntimeError("TWIX file has no image acquisition block supported by the generic fallback.")
    image_obj = mapped["image"]
    image_obj.flags["remove_os"] = True
    image_obj.flags["zf_missing_lines"] = True
    image_obj.flags["average"] = {"Seg"}
    raw = np.asarray(image_obj[:])
    # Collapse non-spatial dimensions conservatively and retain coil dimension where possible.
    raw = np.squeeze(raw)
    if raw.ndim < 2:
        raise RuntimeError(f"Unexpected TWIX image data shape: {raw.shape}")
    while raw.ndim > 3:
        raw = raw[0]
    if raw.ndim == 2:
        kspace = raw
        coil_images = np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(kspace)))
        image = np.abs(coil_images)
    else:
        # The exact mapped dimension order varies by acquisition. The final two axes are treated as spatial.
        kspace = raw
        coil_images = np.fft.fftshift(
            np.fft.ifft2(np.fft.ifftshift(kspace, axes=(-2, -1)), axes=(-2, -1)),
            axes=(-2, -1),
        )
        image = np.sqrt(np.sum(np.abs(coil_images) ** 2, axis=0))
    output_path = output_dir / "siemens_twix_generic_reconstruction.npz"
    np.savez_compressed(output_path, image=image, kspace=kspace, source=str(input_path), backend="twixtools generic")
    return AdapterResult(vendor="Siemens", backend="twixtools generic", output_path=output_path, image=image, kspace=kspace,
                         log=f"TWIX generic reconstruction completed. Raw shape: {raw.shape}")


def reconstruct(vendor_backend: str, input_path: Path, output_dir: Optional[Path] = None) -> AdapterResult:
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    output_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="mri_recon_"))
    output_dir.mkdir(parents=True, exist_ok=True)
    if vendor_backend == "GE Orchestra SDK":
        return reconstruct_ge(input_path, output_dir)
    if vendor_backend == "Siemens IDEA/ICE external recon":
        return reconstruct_siemens_external(input_path, output_dir)
    if vendor_backend == "Siemens TWIX Python fallback":
        return reconstruct_siemens_twix(input_path, output_dir)
    raise ValueError(f"Unknown backend: {vendor_backend}")
