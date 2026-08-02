# CPC format resolution — C0045

The supplied CPC 6.33 treatment export was compared across all fifteen `Spectrum_*.dmp_FFT` and companion `.dmp` files.

## FFT container

Every file has an stable relation:

`validated 8CH FFT snapshots = ceil(declared message entries / 2)`

The old interpretation that half the FFT frames were missing was incorrect. The header count represents paired message entries. Each validated snapshot contains eight channels with 256 float32 bins.

## Companion raw container

The companion file contains sixteen finite float32 arrays with identical measurement counts and stable spacing. They form eight channel pairs. The export does not store semantic labels for the two members, so C0045 retains both and exposes the higher-information member as a generic measurement-history series.

## A/D waveform availability

`Acquisition.ini` specifies 16,384 total samples per measurement, or 2,048 samples per hydrophone. The decompressed companion files are much smaller than the minimum byte count required for the saved measurements. Therefore the per-measurement A/D waveform is not present in this exported container. C0045 reports this explicitly instead of attempting heuristic reconstruction.
