# RC2-R0004 Core Stabilization

- Same-frame UI changes now call ReplayContext.refresh().
- Re-entrant render requests are queued instead of discarded.
- Snapshot contains per-channel spectrum indices.
- Temperature and magnitude list selection consume snapshot indices.
- Current spectrum renderer consumes snapshot mappings.
- ReplayContext is configured with the study sonication count.
- pytest path is deterministic and verification BAT executes the full suite.
- Added regression tests for refresh, queued rendering and per-channel mapping.

## Real treatment regression

`17-00-24_ANx(1).zip` was extracted through ImportService and audited successfully:

- 8 sonications discovered
- 30 CPC spectrum candidates discovered
- 84 replay magnitude frames
- 76 temperature frames
- first magnitude and temperature frame decoded as 256 x 256 for every sonication
- package audit tool now accepts ZIP input directly
