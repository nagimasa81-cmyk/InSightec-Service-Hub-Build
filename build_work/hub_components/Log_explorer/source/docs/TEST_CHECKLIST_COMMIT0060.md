# Commit0060 Test Checklist

1. Build with `01_BUILD_EXE_GITHUB.bat`.
2. Import a folder using the existing manual Smart Discovery workflow.
3. Load a Viewer pane and verify normal row selection does not freeze.
4. Right-click a column header, choose **Filter contains...**, enter a known substring, and verify the table and displayed count change.
5. Choose **Clear pane filter** and verify all rows return.
6. Click Error, Warning, Info, Critical, and All Quick Filter buttons and verify the checked button, row count, and status line update.
7. Combine a Quick Filter and a contains filter, then clear them.
8. Confirm version.json, EXE metadata, output file name, and About/version display identify Commit0060.
