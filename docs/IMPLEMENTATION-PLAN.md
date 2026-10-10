# Persistent engineering intelligence implementation plan

Goal: preserve the original repository while making its memory verifiable,
deduplication reviewable and historical summaries reproducible.

## Design and constraints

- Python 3.12+, JSON Schema 2020-12, pinned jsonschema and PyYAML.
- Keep all nine original seed records and the baseline report unchanged.
- Legacy stories remain valid; new records use schemaVersion 2 and explicit
  productKey, eventKey, milestone, coverage, publishedAt and evidence metadata.
- IDs identify events; updateOf links material updates. Never rewrite prior rows.
- Conservative, deterministic dedupe: exact identity, curated product aliases,
  structured event matching, then similarity for review only. No embedding service.
- Tools have stable registry entries and append-only observations. Stars are
  optional measurements, never invented or equated with adoption.
- Rollups derive from recorded coverage dates, use ISO weeks/calendar months,
  compare preceding equal periods and expose sparse coverage. Counts are signals,
  not evidence of industry adoption. No fabricated baseline observations.
- CI only validates/tests; no scheduled collector or repository write permission.
- Publish ordered commits to main with expected-head checking and no force push.

## Tasks and verification

1. Schemas and validation (`schemas/`, `radar/validation.py`, `tests/test_validation.py`).
   Test invalid dates, YAML duplicate keys, unknown fields, duplicate identities,
   update lineage, report references, tool foreign keys and non-finite numbers.
2. Dedupe (`config/identity.yml`, `radar/dedupe.py`, `tests/test_dedupe.py`).
   Test URL tracking removal without collapsing meaningful query parameters,
   aliases, paraphrases, product isolation, RC/GA, version boundaries, evidence,
   same release with different capabilities and Thai text.
3. History/rollups (`data/tools.jsonl`, `data/tool-observations.jsonl`,
   `radar/rollups.py`, `radar/__main__.py`, `tests/test_rollups.py`).
   Test ISO year boundary, months/leap years, empty periods, deterministic output,
   latest prior observations, percentage denominators and CLI failures.
4. Documentation, templates, hygiene and CI (`README.md`, `docs/`, `templates/`,
   `.github/`, `.gitignore`, `.gitattributes`, `.editorconfig`).
   Run full suite, repository validator, CLI smoke checks and rollup drift check.
5. Read full diff, focused independent adversarial review, fix findings and publish.
   Confirm remote main SHA and GitHub Actions outcome after publication.
