# RC1-C0045 — CPC format resolution

## Root findings

- Across all 15 supplied CPC FFT exports, the header counter is twice the number, except that an odd final message remains unpaired of structurally validated 8-channel FFT snapshots.
- The counter is therefore treated as paired message entries, not as missing independent FFT frames.
- The companion `.dmp` file contains 16 stable float32 history arrays arranged as eight channel pairs.
- The export does not contain the configured 2048-sample/channel A/D payload. Its decompressed size is far below the minimum required storage size, even before record envelopes.
- Measurement history arrays are no longer labelled as calculated energy without evidence.

## Changes

- Dynamic `AcquireInterval` loading from `Acquisition.ini`.
- Explicit message-entry to FFT-snapshot ratio and coverage reporting.
- Raw A/D availability proof and reason string.
- Measurement Timeline and Raw A/D distinction in the UI.
- Correct 8-panel timeline rendering.
- Expanded audit JSON with snapshot, history and raw-A/D evidence.
