from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(slots=True)
class DecodedSpectrum:
    offset: int
    frequency_hz: np.ndarray
    amplitude: np.ndarray
    confidence: float
    main_peak_hz: float | None
    source: Path


class SharedSpectrumDecoder:
    """
    Lightweight shared decoder for Replay integration.

    SpectrumMsg Analyzer remains the detailed reverse-engineering application.
    This decoder evaluates a bounded set of Float32/Little-Endian offsets and
    selects the candidate whose strongest peak is closest to the Xd INI main
    frequency.
    """

    SAMPLE_COUNT = 2048
    MAX_READ_BYTES = 8 * 1024 * 1024


    def decode_frames(
        self,
        path: Path,
        main_frequency_hz: float,
    ) -> list[DecodedSpectrum]:
        """Decode every plausible spectrum block in one SpectrumMsg file.

        Many exported SpectrumMsg files contain more than one spectrum record.
        The previous integration returned only one best block, which made the
        chart static (1/1) and prevented frame synchronization.  This method
        scans aligned Float32 windows, keeps high-quality non-duplicate blocks,
        and falls back to the legacy single-frame decoder when needed.
        """
        data = path.read_bytes()[: self.MAX_READ_BYTES]
        block_bytes = self.SAMPLE_COUNT * 4
        if len(data) < 64:
            return []
        max_frequency_hz = max(main_frequency_hz * 2.2, main_frequency_hz + 200_000.0)
        frames: list[DecodedSpectrum] = []
        # Use 2048-float blocks first; also test a half-block stride so headers
        # and interleaved records do not force all frames off alignment.
        offsets = list(range(0, max(1, len(data)-256), block_bytes))
        offsets += list(range(block_bytes//2, max(1, len(data)-256), block_bytes))
        seen: list[np.ndarray] = []
        for offset in sorted(set(offsets)):
            count=min(self.SAMPLE_COUNT,(len(data)-offset)//4)
            if count < 256:
                continue
            values=np.frombuffer(data,dtype='<f4',count=count,offset=offset).astype(np.float64)
            if float(np.mean(np.isfinite(values))) < .95:
                continue
            amp=np.abs(np.nan_to_num(values,nan=0.0,posinf=0.0,neginf=0.0))
            if not np.any(amp>0):
                continue
            freqs=np.linspace(0.0,max_frequency_hz,num=count,endpoint=False)
            band=(freqs>=200_000.0)&(freqs<=800_000.0)
            if not np.any(band):
                continue
            band_amp=amp[band]
            dynamic=float(np.nanmax(band_amp)/max(float(np.nanmedian(band_amp)),1e-12))
            if not np.isfinite(dynamic) or dynamic < 1.2:
                continue
            # Reject near-identical overlapping candidates.
            signature=np.interp(np.linspace(0,len(band_amp)-1,64),np.arange(len(band_amp)),band_amp)
            signature=signature/max(float(np.nanmax(signature)),1e-12)
            if any(float(np.nanmean(np.abs(signature-prev))) < 0.01 for prev in seen):
                continue
            seen.append(signature)
            peak_i=int(np.argmax(amp))
            peak_hz=float(freqs[peak_i])
            distance=abs(peak_hz-main_frequency_hz)/max(main_frequency_hz,1.0)
            if distance > 0.35:
                continue
            confidence=min(100.0, 35.0 + min(45.0, dynamic*3.0) + max(0.0,20.0*(1.0-distance/0.35)))
            frames.append(DecodedSpectrum(offset=offset,frequency_hz=freqs,amplitude=amp,confidence=round(confidence,1),main_peak_hz=peak_hz,source=path))
        if frames:
            frames.sort(key=lambda f:f.offset)
            return frames
        single=self.decode_file(path,main_frequency_hz)
        return [single] if single is not None else []

    def decode_file(
        self,
        path: Path,
        main_frequency_hz: float,
    ) -> DecodedSpectrum | None:
        data = path.read_bytes()[: self.MAX_READ_BYTES]
        sample_bytes = self.SAMPLE_COUNT * 4
        if len(data) < 64:
            return None

        max_frequency_hz = max(
            main_frequency_hz * 2.2,
            main_frequency_hz + 200_000.0,
        )

        candidate_offsets = {0, 16, 32, 64, 128, 256, 512, 1024}
        for divisor in range(1, 17):
            candidate_offsets.add(
                max(0, (len(data) // divisor) // 4 * 4)
            )
        for offset in range(
            0,
            min(len(data), sample_bytes * 4),
            max(256, sample_bytes // 4),
        ):
            candidate_offsets.add(offset)

        best = None
        best_score = -1.0

        for offset in sorted(candidate_offsets):
            if offset + 16 > len(data):
                continue

            count = min(
                self.SAMPLE_COUNT,
                (len(data) - offset) // 4,
            )
            if count < 64:
                continue

            values = np.frombuffer(
                data,
                dtype="<f4",
                count=count,
                offset=offset,
            ).astype(np.float64)

            finite = np.isfinite(values)
            if float(np.mean(finite)) < 0.95:
                continue

            amplitude = np.abs(
                np.nan_to_num(
                    values,
                    nan=0.0,
                    posinf=0.0,
                    neginf=0.0,
                )
            )

            if not np.any(amplitude > 0):
                continue

            frequencies = np.linspace(
                0.0,
                max_frequency_hz,
                num=count,
                endpoint=False,
            )

            peak_index = int(np.argmax(amplitude))
            peak_frequency = float(frequencies[peak_index])
            distance = abs(
                peak_frequency - main_frequency_hz
            ) / max(main_frequency_hz, 1.0)

            non_negative = float(np.mean(values >= 0))
            dynamic = float(
                np.max(amplitude)
                / max(np.mean(amplitude), 1e-12)
            )
            continuity = 1.0 - min(
                1.0,
                float(np.std(np.diff(amplitude)))
                / max(float(np.std(amplitude)) * 2.0, 1e-12),
            )

            frequency_score = max(0.0, 1.0 - distance)
            dynamic_score = min(1.0, dynamic / 20.0)
            score = (
                frequency_score * 0.55
                + non_negative * 0.15
                + dynamic_score * 0.20
                + continuity * 0.10
            ) * 100.0

            if score > best_score:
                best_score = score
                best = DecodedSpectrum(
                    offset=offset,
                    frequency_hz=frequencies,
                    amplitude=amplitude,
                    confidence=round(score, 1),
                    main_peak_hz=peak_frequency,
                    source=path,
                )

        return best
