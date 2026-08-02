from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import gzip
import struct
import numpy as np

from src.services.hydrophone_calibration_service import HydrophoneCalibrationService


@dataclass(slots=True)
class CpcHydrophoneFrame:
    index: int
    frequency_hz: np.ndarray
    channels: list[np.ndarray]
    raw_channels: list[np.ndarray] = field(default_factory=list)
    duration_s: float = 0.010
    hw_status: int | None = None


@dataclass(slots=True)
class CpcHydrophoneReplay:
    source_fft: Path | None
    source_raw: Path | None
    channel_count: int = 8
    sampling_frequency_hz: float = 0.0
    main_frequency_hz: float = 0.0
    declared_frame_count: int = 0
    declared_message_count: int = 0
    decoded_snapshot_count: int = 0
    messages_per_snapshot: int = 1
    final_snapshot_has_single_message: bool = False
    acquisition_interval_s: float = 0.010
    raw_adc_available: bool = False
    raw_adc_unavailable_reason: str = ""
    total_samples: int = 0
    frames: list[CpcHydrophoneFrame] = field(default_factory=list)
    channel_reference_levels: list[float] = field(default_factory=lambda: [1.0] * 8)
    display_db_min: float = -60.0
    display_db_max: float = 0.0
    note: str = ""
    decoder_confidence: str = "failed"
    raw_timeline_channels: list[np.ndarray] = field(default_factory=list)
    raw_history_pairs: list[tuple[np.ndarray, np.ndarray]] = field(default_factory=list)
    raw_timeline_time_s: np.ndarray = field(default_factory=lambda: np.array([], dtype=float))
    raw_container_total_measurements: int = 0
    raw_container_saved_measurements: int = 0
    raw_structure_note: str = ""

    @property
    def frame_interval_s(self) -> float:
        values = [f.duration_s for f in self.frames if np.isfinite(f.duration_s) and f.duration_s > 0]
        return float(np.median(values)) if values else 0.010


class HydrophoneReplayService:
    """Decode CPC Spectrum containers without mixing Sonication SpectrumMsg data.

    Header fields of the FFT container are stable in the supplied exports:
    saved-measure count, 8 channels, 16384 acquisition samples, FFT processing
    length, sample rate and sonication frequency.  The vendor record payload is
    not publicly documented, therefore record slicing is isolated and labelled
    diagnostic.  All analysis is calculated from decoded CPC payloads only.
    """

    DEFAULT_BANDS_MHZ = (
        (0.25, 0.30), (0.30, 0.35), (0.35, 0.40),
        (0.40, 0.50), (0.50, 0.65), (0.65, 0.80),
    )

    @staticmethod
    def _read_blob(path: Path | None) -> bytes:
        if path is None:
            return b""
        try:
            with gzip.open(path, "rb") as stream:
                return stream.read()
        except OSError:
            return path.read_bytes()

    def select_files(self, cpc_files: list[Path], sonication_index: int, sonication_count: int) -> tuple[Path | None, Path | None]:
        fft_files = sorted(p for p in cpc_files if p.name.lower().endswith(".dmp_fft"))
        raw_files = sorted(p for p in cpc_files if p.name.lower().startswith("spectrum_") and p.name.lower().endswith(".dmp"))

        def select(items: list[Path]) -> Path | None:
            if not items:
                return None
            mapped = items[-sonication_count:] if sonication_count and len(items) >= sonication_count else items
            return mapped[min(max(sonication_index, 0), len(mapped) - 1)]

        return select(fft_files), select(raw_files)

    def build(self, cpc_files: list[Path], sonication_index: int, sonication_count: int) -> CpcHydrophoneReplay:
        fft_path, raw_path = self.select_files(cpc_files, sonication_index, sonication_count)
        result = CpcHydrophoneReplay(source_fft=fft_path, source_raw=raw_path)
        calibration = None
        if fft_path is not None:
            calibration = HydrophoneCalibrationService().read(next((p for p in fft_path.parents if p.name.lower() == "cpcfiles"), fft_path.parent))
        fft_blob = self._read_blob(fft_path)
        if len(fft_blob) < 40:
            result.note = "No valid CPC Spectrum_*.dmp_FFT container was mapped."
            return result

        first, frame_count, channel_count, total_samples, processing, sample_rate = struct.unpack("<6I", fft_blob[:24])
        main_frequency = struct.unpack("<d", fft_blob[32:40])[0]
        result.channel_count = int(channel_count)
        result.sampling_frequency_hz = float(sample_rate)
        result.main_frequency_hz = float(main_frequency)
        result.declared_frame_count = int(frame_count)
        result.declared_message_count = int(frame_count)
        result.total_samples = int(total_samples)
        if channel_count != 8 or frame_count <= 0:
            result.note = f"Unsupported CPC FFT header: channels={channel_count}, measures={frame_count}."
            return result

        fft_frames = self._decode_fft_payload(fft_blob[40:], frame_count, channel_count, sample_rate)
        result.decoded_snapshot_count = len(fft_frames)
        # All supplied CPC 6.33 exports show an exact 2:1 relation between the
        # header counter and validated 8CH spectrum snapshots. The header field
        # therefore represents paired message entries, not independent FFT frames.
        if fft_frames and len(fft_frames) == (frame_count + 1) // 2:
            result.messages_per_snapshot = 2
            result.final_snapshot_has_single_message = bool(frame_count % 2)
        elif fft_frames:
            result.messages_per_snapshot = max(1, round(frame_count / len(fft_frames)))
        raw_blob = self._read_blob(raw_path)
        raw_frames = self._decode_raw_payload(raw_blob, len(fft_frames), channel_count, total_samples)
        config = self._load_acquisition_config(raw_path)
        result.acquisition_interval_s = float(config.get("acquire_interval_ms", 10.0)) / 1000.0
        timeline, timeline_info = self._decode_raw_timeline(raw_blob, int(first), channel_count)
        result.raw_timeline_channels = timeline
        if timeline:
            result.raw_timeline_time_s = np.arange(len(timeline[0]), dtype=float) * result.acquisition_interval_s
        result.raw_container_total_measurements = int(timeline_info.get("total_measurements", 0))
        result.raw_container_saved_measurements = int(timeline_info.get("saved_measurements", 0))
        result.raw_structure_note = str(timeline_info.get("note", ""))
        result.raw_history_pairs = list(timeline_info.get("pairs", []))
        for index, (freq, channels) in enumerate(fft_frames):
            raw = raw_frames[index] if index < len(raw_frames) else []
            calibrated_channels = [
                calibration.apply(freq, values, channel_index) if calibration is not None and calibration.available else np.asarray(values, dtype=float)
                for channel_index, values in enumerate(channels)
            ]
            result.frames.append(CpcHydrophoneFrame(index, freq, calibrated_channels, raw_channels=raw))

        result.channel_reference_levels = self._references(result.frames)
        result.decoder_confidence = "validated_fft" if result.frames else "failed"
        result.raw_adc_available = any(f.raw_channels for f in result.frames)
        expected_adc_bytes = int(result.raw_container_saved_measurements or frame_count) * int(total_samples) * 2
        if not result.raw_adc_available:
            result.raw_adc_unavailable_reason = (
                f"The exported raw companion decompresses to {len(raw_blob):,} bytes, while even "
                f"{int(result.raw_container_saved_measurements or frame_count)} saved measurements × "
                f"{total_samples} int16 samples require at least {expected_adc_bytes:,} bytes before "
                "record envelopes. The 2048-sample/channel A/D payload is therefore not present in "
                "this export container; only measurement-history arrays are available."
            )
        if any(f.raw_channels for f in result.frames):
            result.decoder_confidence = "validated_fft_and_raw"
        raw_state = "validated raw waveform decoded" if any(f.raw_channels for f in result.frames) else ("validated 8CH measurement timeline decoded; per-measure waveform still under structural validation" if result.raw_timeline_channels else "raw waveform not verified; raw container not decoded")
        result.note = (
            f"Independent CPC 8CH analyzer: {len(result.frames)} validated 8CH FFT snapshots "
            f"from {frame_count} message entries (paired per snapshot; final entry may be unpaired), {raw_state}, "
            f"Fs={sample_rate/1e6:.3f} MHz, sonication={main_frequency/1e6:.3f} MHz. "
            "FFT blocks and the independent 8CH measurement-history arrays are structurally validated; spectrogram and editable band energy are calculated locally. "
            "The proprietary per-record envelope remains diagnostic; channel labels CH0–CH7 are preserved, physical positions are not inferred. "
            + (f"Calibration applied from {calibration.calibration_ini.name}; SpectrumFactor={calibration.spectrum_factors}." if calibration is not None and calibration.available and calibration.calibration_ini else "Calibration file not found; unity coefficients used.")
        )
        return result

    @staticmethod
    def _load_acquisition_config(raw_path: Path | None) -> dict[str, float]:
        """Read CPC Acquisition.ini values from the extracted package when present."""
        result: dict[str, float] = {}
        if raw_path is None:
            return result
        candidates = []
        for parent in [raw_path.parent, *raw_path.parents[:4]]:
            candidates.extend([parent / "App" / "Ini" / "Acquisition.ini", parent / "Acquisition.ini"])
        for ini in candidates:
            if not ini.exists():
                continue
            try:
                for raw_line in ini.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = raw_line.split(";", 1)[0].strip()
                    if "=" not in line:
                        continue
                    key, value = [x.strip() for x in line.split("=", 1)]
                    if key.lower() == "acquireinterval":
                        result["acquire_interval_ms"] = float(value)
                    elif key.lower() == "sizeofmeasurmentdata":
                        result["measurement_samples_total"] = float(value)
                    elif key.lower() == "sizeofoutputgraph":
                        result["fft_output_graph"] = float(value)
                return result
            except Exception:
                continue
        return result

    @staticmethod
    def _decode_fft_payload(payload: bytes, frame_count: int, channel_count: int, sample_rate: float) -> list[tuple[np.ndarray, list[np.ndarray]]]:
        """Decode validated CPC FFT channel blocks.

        Real CPC exports store each channel spectrum as a 32-bit bin-count marker
        (normally 256), followed by that many float32 bins.  Channel blocks are
        separated by a fixed metadata envelope, and eight consecutive markers
        form one saved measure.  This parser intentionally rejects the old
        equal-slice heuristic.
        """
        if channel_count != 8 or len(payload) < 4096:
            return []
        blob = memoryview(payload)
        markers=[]
        for off in range(0, len(blob)-4, 4):
            n=struct.unpack_from('<I', blob, off)[0]
            if 16 <= n <= 8192 and off + 4 + n*4 <= len(blob):
                vals=np.frombuffer(blob[off+4:off+4+n*4], dtype='<f4')
                finite=np.isfinite(vals)
                if finite.mean() > .995 and np.nanmax(np.abs(vals[finite])) < 1e12:
                    markers.append((off,n))
        groups=[]
        i=0
        while i+7 < len(markers):
            cand=markers[i:i+8]
            if len({n for _,n in cand})==1:
                gaps=np.diff([o for o,_ in cand])
                if np.all(gaps==gaps[0]) and gaps[0] >= 4+cand[0][1]*4:
                    groups.append(cand); i+=8; continue
            i+=1
        frames=[]
        for group in groups[:frame_count]:
            bins=group[0][1]
            channels=[]
            valid=True
            for off,n in group:
                arr=np.frombuffer(blob[off+4:off+4+n*4], dtype='<f4').astype(float)
                if len(arr)!=bins or not np.all(np.isfinite(arr)):
                    valid=False; break
                channels.append(np.abs(arr))
            if not valid: continue
            freq=np.linspace(0.0, sample_rate/2.0, bins, endpoint=False, dtype=float)
            frames.append((freq,channels))
        return frames


    @staticmethod
    def _decode_raw_timeline(blob: bytes, expected_total_measurements: int, channel_count: int) -> tuple[list[np.ndarray], dict[str, object]]:
        """Decode the CPC .dmp measurement-history arrays without calling them ADC waveforms.

        In the supplied CPC 6.33 export the raw companion container begins with a
        compact header and then contains sixteen equally spaced arrays whose
        element count equals the FFT container's total-measurement counter.  The
        arrays occur as eight pairs: an all-zero optional spectrum-signal history
        followed by the calculated-energy history for CH0..CH7.  This matches the
        CPC screen's Energy-per-Band timeline and the Acquisition.ini setting that
        external modules receive periodic Spectrum messages.

        This parser validates count markers, equal spacing, finite float32 payloads,
        eight non-zero channel histories, and monotonic record geometry.  It does
        not mislabel these histories as a 2048-sample A/D waveform.
        """
        info: dict[str, object] = {"total_measurements": 0, "saved_measurements": 0, "note": ""}
        if len(blob) < 128 or channel_count != 8 or expected_total_measurements < 16:
            return [], info
        try:
            saved = int(struct.unpack_from("<I", blob, 0)[0])
        except struct.error:
            return [], info
        marker = struct.pack("<I", expected_total_measurements)
        offsets = []
        start = 0
        while True:
            pos = blob.find(marker, start)
            if pos < 0:
                break
            if pos % 4 == 0 and pos + 4 + expected_total_measurements * 4 <= len(blob):
                values = np.frombuffer(blob, dtype="<f4", count=expected_total_measurements, offset=pos + 4)
                if np.all(np.isfinite(values)) and float(np.max(np.abs(values))) < 1e6:
                    offsets.append(pos)
            start = pos + 1
        if len(offsets) < 16:
            info["note"] = f"Only {len(offsets)} validated history arrays found; 16 required."
            return [], info
        # Select a 16-array run with near-constant spacing.
        run = None
        for i in range(len(offsets) - 15):
            cand = offsets[i:i+16]
            gaps = np.diff(cand)
            if np.max(gaps) - np.min(gaps) <= 8 and np.median(gaps) >= 4 + expected_total_measurements * 4:
                run = cand
                break
        if run is None:
            info["note"] = "History markers exist but no stable 16-array CPC layout was found."
            return [], info
        arrays = [np.frombuffer(blob, dtype="<f4", count=expected_total_measurements, offset=o+4).astype(float, copy=True) for o in run]
        # The 16 arrays form eight stable pairs. Their semantic labels are not
        # stored in the export, so retain both arrays and expose the non-zero
        # member as a generic measurement-history series rather than calling it
        # calculated energy.
        pairs = [(arrays[2*ch], arrays[2*ch+1]) for ch in range(8)]
        history = [b if float(np.std(b)) >= float(np.std(a)) else a for a, b in pairs]
        if any(not np.all(np.isfinite(a)) for a in history):
            return [], info
        if sum(float(np.std(a)) > 0.0 for a in history) < 6:
            info["note"] = "CPC history arrays were found but too few channels carry signal."
            return [], info
        info.update({
            "total_measurements": expected_total_measurements,
            "saved_measurements": saved,
            "pairs": pairs,
            "note": (f"Validated CPC history layout: eight channel-pairs × {expected_total_measurements} measurements; "
                     f"container header saved-count={saved}; marker spacing≈{int(np.median(np.diff(run)))} bytes. "
                     "These are measurement histories, not the 2048-sample per-channel A/D waveform."),
        })
        return history, info

    @staticmethod
    def _decode_raw_payload(blob: bytes, expected_frames: int, channel_count: int, expected_samples: int = 16384) -> list[list[np.ndarray]]:
        """Decode raw samples only when a full, structurally valid 8CH payload exists.

        The supplied .dmp file is an energy/packet stream rather than a verified
        16384-sample waveform container.  Returning no data is safer than showing
        header bytes as ADC samples.  Future format-specific decoders can be added
        here without changing the UI/API.
        """
        if len(blob) < 40 or expected_frames <= 0 or channel_count != 8:
            return []
        required=expected_samples*channel_count*2
        payload=blob[40:]
        if len(payload) < required*expected_frames:
            return []
        # Accept only exact contiguous int16 frames; reject envelopes/remainders.
        if len(payload) != required*expected_frames:
            return []
        out=[]
        for i in range(expected_frames):
            chunk=payload[i*required:(i+1)*required]
            matrix=np.frombuffer(chunk,dtype='<i2').reshape(expected_samples,channel_count).T
            out.append([row.astype(float,copy=True) for row in matrix])
        return out

    @staticmethod
    def _references(frames: list[CpcHydrophoneFrame]) -> list[float]:
        refs: list[float] = []
        tiny = np.finfo(float).tiny
        for ch in range(8):
            levels = []
            for frame in frames:
                if ch >= len(frame.channels):
                    continue
                amp = np.asarray(frame.channels[ch], dtype=float)
                freq = np.asarray(frame.frequency_hz, dtype=float)
                mask = np.isfinite(amp) & (amp > 0) & np.isfinite(freq) & (freq >= 50_000) & (freq <= 1_000_000)
                if np.any(mask):
                    levels.append(float(np.percentile(amp[mask], 99.5)))
            refs.append(max(float(np.median(levels)) if levels else 1.0, tiny))
        return refs

    @staticmethod
    def relative_db(replay: CpcHydrophoneReplay, frame: CpcHydrophoneFrame, channel: int) -> np.ndarray:
        amp = np.asarray(frame.channels[channel], dtype=float)
        ref = max(float(replay.channel_reference_levels[channel]), np.finfo(float).tiny)
        floor = ref * 10.0 ** (replay.display_db_min / 20.0)
        safe = np.maximum(np.where(np.isfinite(amp), np.abs(amp), 0.0), floor)
        return np.clip(20.0 * np.log10(safe / ref), replay.display_db_min, replay.display_db_max)

    def spectrogram(self, replay: CpcHydrophoneReplay, channel: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if not replay.frames:
            return np.array([]), np.array([]), np.empty((0, 0))
        min_bins = min(len(f.channels[channel]) for f in replay.frames)
        matrix = np.vstack([self.relative_db(replay, f, channel)[:min_bins] for f in replay.frames])
        freq = replay.frames[0].frequency_hz[:min_bins]
        time = np.arange(len(replay.frames), dtype=float) * replay.frame_interval_s
        return time, freq, matrix

    def band_energy(self, replay: CpcHydrophoneReplay, low_hz: float, high_hz: float) -> np.ndarray:
        output = np.full((len(replay.frames), replay.channel_count), np.nan, dtype=float)
        for i, frame in enumerate(replay.frames):
            freq = np.asarray(frame.frequency_hz, dtype=float)
            mask = (freq >= low_hz) & (freq <= high_hz)
            if not np.any(mask):
                continue
            for ch in range(min(replay.channel_count, len(frame.channels))):
                amp = np.asarray(frame.channels[ch], dtype=float)
                n = min(len(amp), len(mask))
                local = mask[:n]
                if np.any(local):
                    output[i, ch] = float(np.trapezoid(np.square(np.abs(amp[:n][local])), freq[:n][local]))
        return output

    def frame_statistics(self, replay: CpcHydrophoneReplay, frame_index: int, low_hz: float, high_hz: float) -> list[dict[str, float]]:
        if not replay.frames:
            return []
        frame = replay.frames[min(max(frame_index, 0), len(replay.frames)-1)]
        rows = []
        for ch in range(replay.channel_count):
            amp = np.asarray(frame.channels[ch], dtype=float)
            freq = np.asarray(frame.frequency_hz, dtype=float)
            n = min(len(amp), len(freq)); amp = amp[:n]; freq = freq[:n]
            valid = np.isfinite(amp) & np.isfinite(freq)
            peak_i = int(np.argmax(np.where(valid, amp, -np.inf))) if np.any(valid) else 0
            mask = valid & (freq >= low_hz) & (freq <= high_hz)
            energy = float(np.trapezoid(np.square(amp[mask]), freq[mask])) if np.count_nonzero(mask) > 1 else float("nan")
            raw = np.asarray(frame.raw_channels[ch], dtype=float) if ch < len(frame.raw_channels) else np.array([])
            rows.append({
                "channel": float(ch),
                "raw_peak": float(np.max(np.abs(raw))) if raw.size else float("nan"),
                "raw_rms": float(np.sqrt(np.mean(np.square(raw)))) if raw.size else float("nan"),
                "dominant_hz": float(freq[peak_i]) if n else float("nan"),
                "peak_db": float(self.relative_db(replay, frame, ch)[peak_i]) if n else float("nan"),
                "band_energy": energy,
            })
        return rows
