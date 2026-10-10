# Upgrade verification — 2026-10-10

Local checks were run with Python 3.12 on Windows using the exact hash-locked
dependencies installed into an isolated workspace directory.

## Behavioral suite

Command: `python -m unittest discover -v`

```text
Ran 55 tests in 13.973s

OK
```

Coverage includes malformed JSON/YAML, schema/date/enum rules, references,
legacy-v2 compatibility, semantic duplicates, aliases, version delimiters,
material-update evidence, persisted review audit records, period boundaries,
missing measurements, observation-derived links, drift and actual CLI behavior.

New logic and the review fixes were exercised with failing tests before fixes.
An independent adversarial reviewer found two actionable issues: eventKey-only
renaming could bypass materiality, and supplied reviews were not always checked.
Both were reproduced, fixed and included in the final green suite.

## Runtime and artifact checks

```text
Validation passed
{"decision": "NEW", "reason": "no prior identity or review signal found", "matchedId": null}
Rollup check passed
```

Commands: `python -m radar validate --base <local baseline SHA>`,
`python -m radar dedupe templates/story.json`, `python -m radar rollup --check`.
The real append-only test initializes Git history and rejects modified old rows.

Independent artifact checks confirmed all seven schemas and three JSON templates,
read-only workflow permissions and full action SHAs. Both views matched the nine
seed events, one day with stories, null growth baselines and the C# Dev Kit story
link. Original seed/report, license and three policy configs were byte-identical.

`python -m compileall -q radar tests` and `git diff --cached --check` passed.
Installing requirements.lock with `--require-hashes` succeeded in a clean target.

## Scope and limitations

This document records local checks before publication. GitHub-hosted Linux,
Python 3.13 and Windows workflow results are recorded by GitHub Actions after
the commits reach main. No external scheduler or fresh-news collection was run.
Seed release claims were preserved, not newly fact-checked.
