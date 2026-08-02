# RC1-C0043 — Validated CPC Binary Decoder

- Preserves all accepted C0043 UI/build/discovery work.
- Replaces equal-slice FFT guessing with structural 8-channel bin-block parsing.
- Rejects implausible float payloads and prevents 1e38 artifacts.
- Disables raw waveform display unless a complete 8 x 16384 int16 payload is proven.
- Adds explicit decoder confidence states.
- Prevents derived FFT/statistics from unverified raw bytes.
