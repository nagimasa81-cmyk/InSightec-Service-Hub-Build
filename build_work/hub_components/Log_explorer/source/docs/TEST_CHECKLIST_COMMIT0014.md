# Commit0014 Test Checklist

## Feedback Engine
- [ ] Feedback button opens.
- [ ] Category, priority and reproducibility can be selected.
- [ ] Comment and attachments can be added.
- [ ] Feedback template TXT is created.
- [ ] Feedback manifest JSON is created with schema `insightec.feedback.v1`.
- [ ] Runtime context includes source folder, output folder and installed file types.

## ZIP single-file import
- [ ] Import > Import selected file accepts `.zip`.
- [ ] ZIP with one supported file selects it automatically.
- [ ] ZIP with multiple supported files shows a selection list.
- [ ] Exactly one file is extracted and imported.
- [ ] Temporary extracted data is cleaned after import.
- [ ] ZIP path traversal entries are rejected.
- [ ] ZIP with no supported log gives a clear error.
- [ ] Direct `.txt`, `.log`, `.out` and `.ar` imports still work.

## Regression
- [ ] File Type Update ZIP install still works.
- [ ] VIMeasure plugin remains installed/reloadable.
- [ ] Existing Viewer and Merge flows still start.
