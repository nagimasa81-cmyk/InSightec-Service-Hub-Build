# Commit0062

Fixed the Viewer right-click filter crash caused by `unicodedata` being placed inside the module docstring. Quick Filter behavior is unchanged.

# Release Notes

## Commit0060 — Viewer Filter Action Recovery

- Restored the right-click **Filter contains...** and **Filter exact...** actions on Viewer column headers.
- Rebound every Quick Filter button to the final filter engine after all UI overrides are installed.
- Added visible filter status and displayed-row counts after each action.
- Preserved Commit0059a file loading and click-freeze stability.
- Updated version.json, BAT metadata, executable names, tests, and validation documents.

# Log Merge Tool RC1 Release Notes

## Commit0059 — Viewer Click Freeze Fix
- Restores the original manual Smart Discovery workflow from Commit0053a.
- Prevents Event Sync from running on programmatic selection changes.
- Applies synchronized selections in one batch with bounded highlighting.
- Aligns active source version, version.json, build scripts, executable metadata, and validation files.

## Commit0009 RC1 Evaluation Build
This build integrates Investigation Workspace into the existing RC1 Foundation and corrects the WaterSystem viewer parser mapping issue reported during evaluation.

Primary evaluation focus:
1. Investigation templates and time synchronization.
2. WaterSystem Event / Level / Message extraction.
3. No regression in existing Viewer, Discovery and Merge behavior.
