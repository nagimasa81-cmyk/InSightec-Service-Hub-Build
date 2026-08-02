# C0031 Replay Timeline / Hydrophone Synchronization

- Maps the final N CPC `Spectrum_*.dmp` measurements to Sonication 1..N.
- Prevents all CPC spectrum measurements from being merged into every selected sonication.
- Hydrophone table and acoustic spectrum now rebuild from the selected Sonication only.
- Keeps Relative Acoustic Spectrum hidden pending validated physical mapping.
- Refreshes SkullMeasures data whenever the XD window opens or Sonication changes.
- Labels the replay cursor as MR acquisition elapsed time.
