Commit0014 Revision 2

ZIP import now follows this path:

ZIP -> safe temporary extraction -> Smart File Discovery -> multiple recognized
file selection -> parse into memory -> delete temporary extraction -> Viewer.

UNKNOWN is excluded from this ZIP workflow.
Nested ZIP archives are not expanded; their file names are reported only.
