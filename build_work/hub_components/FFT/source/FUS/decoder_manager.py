from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib.util import find_spec
import json
import os
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DicomDecodeResult:
    array: Any
    transfer_syntax: str
    decoder: str


class DicomDecodeError(RuntimeError):
    """Raised when DICOM pixel data cannot be decoded safely."""


@dataclass(frozen=True)
class DecoderCapabilities:
    pylibjpeg: bool
    libjpeg: bool
    openjpeg: bool
    jpeg_ls: bool


def decoder_capabilities() -> DecoderCapabilities:
    """Report optional codec availability without importing codec modules."""
    return DecoderCapabilities(
        pylibjpeg=_has_module("pylibjpeg"),
        libjpeg=_has_module("libjpeg"),
        openjpeg=_has_module("openjpeg"),
        jpeg_ls=_has_module("jpeg_ls") or _has_module("pyjpegls"),
    )


def _diagnostic_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MR_Image_Explorer"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except Exception:
        base = Path.cwd()
    return base / "dicom_decoder.log"


def _write_diagnostic(**record: Any) -> None:
    """Append a compact JSON record; diagnostics must never break viewing."""
    payload = {
        "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **record,
        "capabilities": asdict(decoder_capabilities()),
    }
    try:
        with _diagnostic_path().open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def _transfer_syntax(dataset: Any) -> str:
    try:
        uid = getattr(getattr(dataset, "file_meta", None), "TransferSyntaxUID", None)
        return str(uid) if uid is not None else "unknown"
    except Exception:
        return "unknown"


def _has_module(name: str) -> bool:
    try:
        return find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _select_decoder(transfer_syntax: str) -> tuple[str | None, str | None]:
    """Return (pydicom plugin name, missing dependency hint).

    No optional decoder module is imported here. This function is called only
    when a DICOM image is opened, never during application startup.
    """
    # RLE Lossless is handled by pydicom's built-in decoder.
    if transfer_syntax == "1.2.840.10008.1.2.5":
        return "pydicom", None

    # JPEG-LS requires the optional pyjpegls package.
    if transfer_syntax in {"1.2.840.10008.1.2.4.80", "1.2.840.10008.1.2.4.81"}:
        if _has_module("jpeg_ls") or _has_module("pyjpegls"):
            return "pyjpegls", None
        return None, "Install pyjpegls to decode JPEG-LS DICOM images."

    # JPEG 2000 is provided through pylibjpeg-openjpeg.
    if transfer_syntax in {"1.2.840.10008.1.2.4.90", "1.2.840.10008.1.2.4.91"}:
        if _has_module("openjpeg") and _has_module("pylibjpeg"):
            return "pylibjpeg", None
        return None, "Install pylibjpeg and pylibjpeg-openjpeg to decode JPEG 2000 DICOM images."

    # JPEG Baseline/Extended/Lossless family is provided through pylibjpeg-libjpeg.
    if transfer_syntax.startswith("1.2.840.10008.1.2.4."):
        if _has_module("libjpeg") and _has_module("pylibjpeg"):
            return "pylibjpeg", None
        return None, "Install pylibjpeg and pylibjpeg-libjpeg to decode JPEG-compressed DICOM images."

    # Uncompressed transfer syntaxes and any syntax pydicom can handle directly.
    return None, None


def _decode_with_dataset(dataset: Any, plugin: str | None) -> Any:
    """Decode through pydicom without importing a decoder during startup."""
    if plugin and hasattr(dataset, "pixel_array_options"):
        dataset.pixel_array_options(decoding_plugin=plugin)
    return dataset.pixel_array


def decode_dicom_pixels(dataset: Any) -> DicomDecodeResult:
    """Decode DICOM pixels only when an image is opened.

    The transfer syntax is inspected first. Only the required decoder backend is
    selected, and GDCM is never required or imported. Uncompressed images use
    pydicom directly; compressed images use explicitly packaged optional codecs.
    """
    transfer_syntax = _transfer_syntax(dataset)
    plugin, missing_hint = _select_decoder(transfer_syntax)

    if missing_hint:
        _write_diagnostic(event="missing_decoder", transfer_syntax=transfer_syntax, hint=missing_hint)
        raise DicomDecodeError(
            f"DICOM pixel decoding is unavailable for Transfer Syntax {transfer_syntax}. "
            f"{missing_hint} The viewer itself can continue running."
        )

    try:
        array = _decode_with_dataset(dataset, plugin)
        result = DicomDecodeResult(array=array, transfer_syntax=transfer_syntax, decoder=plugin or "pydicom-auto")
        _write_diagnostic(event="decode_success", transfer_syntax=transfer_syntax, decoder=result.decoder, shape=getattr(array, "shape", None))
        return result
    except Exception as exc:
        _write_diagnostic(event="decode_failure", transfer_syntax=transfer_syntax, decoder=plugin or "pydicom-auto", error=f"{type(exc).__name__}: {exc}")
        plugin_text = plugin or "pydicom automatic decoder"
        raise DicomDecodeError(
            "DICOM pixel decoding failed. "
            f"Transfer Syntax: {transfer_syntax}; selected decoder: {plugin_text}. "
            "The application remains usable for other images. Original error: "
            f"{exc}"
        ) from exc
