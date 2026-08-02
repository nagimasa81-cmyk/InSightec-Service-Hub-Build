# RC2 Architecture

## Single source of truth
`ReplayContext` owns sonication, frame and channel selection. UI controls never render directly.

## Synchronized render path
`ReplayContext -> ReplayViewCoordinator -> registered replay views`

R0002 registers the current frame bundle as the first migrated view. The render bundle updates image/thermal overlay, temperature cursor, acoustic spectrum, power/score, statistics and synchronized labels from the same immutable selection.

Independent widget frame cursors are prohibited.
