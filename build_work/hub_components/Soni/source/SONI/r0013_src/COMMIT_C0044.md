# RC1-C0045 — CPC Raw Container Deep Structure Analysis

- Preserves the validated C0043 FFT decoder and analyzer UI.
- Decodes the CPC raw companion file's 16-array history layout.
- Exposes eight validated channel measurement timelines using the total-measurement counter.
- Stops treating the history arrays as per-measure ADC samples.
- Shows the validated timeline in the Raw Data tab until the 2048-sample A/D packet layout is proven.
- Adds structural diagnostics for marker count, spacing, saved count and total measurement count.
