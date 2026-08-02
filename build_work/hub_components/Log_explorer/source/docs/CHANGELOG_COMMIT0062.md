# Commit0062

## Right-click filter crash fix

- Moved `import unicodedata` out of the module docstring into the executable import section.
- Fixed `NameError: unicodedata is not defined` when selecting Viewer right-click filter actions.
- Kept the working Commit0061 Quick Filter implementation unchanged.
- Added a regression test that imports the module and executes the normalization function.
