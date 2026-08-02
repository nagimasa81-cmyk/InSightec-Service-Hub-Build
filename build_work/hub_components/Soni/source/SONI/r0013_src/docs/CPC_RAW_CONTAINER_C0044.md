# CPC raw companion analysis (C0045)

The supplied Acquisition.ini states `SizeOfMeasurmentData=16384`, which is the total across eight hydrophones, therefore 2048 acquisition samples per channel. It also states `SizeOfOutputGraph=2048`, `AcquireInterval=10 ms`, and raw-data saving enabled.

The supplied `.dmp` companion does not contain a simple sequence of 96 × 8 × 2048 int16 samples. Its validated structure contains sixteen float32 histories whose length equals the FFT header total-measurement count. They are arranged as eight pairs. In this dataset the first array of every pair is zero and the second is a non-zero calculated-energy/signal history.

For the analyzed Sonication 7 companion:

- FFT total measurements: 2249
- FFT saved measurements: 96
- raw companion header count: 66
- validated history arrays: 16
- channel timelines: 8 × 2249
- marker spacing: approximately 9022 bytes

C0045 displays these histories, but deliberately does not call them A/D waveforms. The remaining task is to identify the per-saved-measure 2048-sample packet encoding inside the FFT/raw record envelope or establish that the export omits it.
