# Commit0043 — Foundation Cleanup

- Removed Commit0037–0042 overlapping final patch blocks.
- Installed one canonical Review parser for Discovery, ZIP cache and Viewer.
- Review display is fixed to Category=Parameter and Message=Value.
- Removed Review Raw JSON column expansion.
- Removed direct CSA/CGA `Type=Err` startup assignments.
- START remains Viewer-only and Merge remains disabled.
- Default Viewer is Dual; Show 1–4 and splitter resizing remain available.

Earlier feature patches before Commit0037 remain until they are migrated into
dedicated modules in later Foundation commits.
