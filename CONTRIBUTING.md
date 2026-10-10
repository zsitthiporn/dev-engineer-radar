# Contributing

Preserve the Thai reporting style and English technical names. Read
[the producer runbook](docs/RUNBOOK.md) before adding radar records.

Use Python 3.12 or 3.13 in a virtual environment, then install the hash-locked
requirements. No network or model provider is needed to validate, test or dedupe.

```console
python -m pip install --require-hashes -r requirements.lock
python -m radar validate
python -m unittest discover -v
python -m radar rollup --check
```

For data changes, regenerate derived files with the coverage cutoff date:
`python -m radar rollup --as-of YYYY-MM-DD`. Include the manifest and all changed
rollups in the same commit. A repeated date is reproducible; no timestamps or
random scores are added. Future observations are excluded from past snapshots.

Keep changes focused. Do not reorder or rewrite existing JSONL rows. Report
factual corrections in a subsequent linked record/report; use a separately
reviewed correction workflow if an existing row truly needs correction, because
normal CI rejects history edits. Do not disable the append-only check to publish.

Dependency updates are deliberate: review direct requirements and resolved
transitive versions, retrieve SHA-256 hashes from the corresponding PyPI release,
update requirements.lock, install with `--require-hashes`, then rerun CI. Keep all
supported platform wheels in the hash list. Dependabot proposes Actions updates;
Python locks are updated manually so approved versions and hashes stay consistent.
