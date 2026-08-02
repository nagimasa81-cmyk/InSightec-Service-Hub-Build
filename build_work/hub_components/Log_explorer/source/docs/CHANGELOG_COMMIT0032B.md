# Commit0032B — GESYS / LAIS / PSC / review.out Recovery

## Critical correction
Restores the complete import path for:

- GESYS / gesyslog
- LAIS
- PSC / psc.log
- review.out and review.out variants

## Detection
- Filename detection supports common prefixes, separators and archive suffixes.
- Content probing is used when files were renamed.
- review.out is identified before generic extension rules.

## Parsing
- Existing dedicated parsers are attempted first.
- A loss-tolerant fallback parser retains every non-empty line.
- Missing timestamps no longer cause the entire line to be discarded.
- UTF-8, UTF-8 BOM, Windows-1252 and Latin-1 are attempted.

## Integration
- Parser registries are updated dynamically.
- Supported-type collections are extended.
- Canonical names match Viewer source names:
  GESYS, LAIS, PSC and Review.
