# Dev Engineer Radar

[![Validate radar](https://github.com/zsitthiporn/dev-engineer-radar/actions/workflows/validate.yml/badge.svg)](https://github.com/zsitthiporn/dev-engineer-radar/actions/workflows/validate.yml)

Personal engineering intelligence for developer tools, AI engineering, .NET/backend,
Kubernetes/DevOps, GitOps, infrastructure and observability. Reports use Thai prose
and English product/technical names. Git is the persistent memory and audit trail.

Public reading site: [Dev Engineer Radar](https://zsitthiporn.github.io/dev-engineer-radar-web/).
The public [deploy repository](https://github.com/zsitthiporn/dev-engineer-radar-web)
contains only the reviewed web projection; this intelligence repository remains private.

## Quick start

Use Python 3.12 or 3.13 in a virtual environment.

```console
python -m venv .venv
# Activate .venv using your operating system's standard activation command.
python -m pip install --require-hashes -r requirements.lock
python -m radar validate
python -m unittest discover -v
python -m radar dedupe templates/story.json
python -m radar rollup --check
```

Dedupe prints a JSON decision: `NEW`, `DUPLICATE`, `UPDATE` or `REVIEW`.
All valid decisions exit 0; inspect the decision, not only the exit status.
Invalid input/history exits 1. It never appends or changes records.

After recording new coverage, run `python -m radar rollup --as-of YYYY-MM-DD`.
Commit reports, history, observations, manifest and derived files together.
See [the producer runbook](docs/RUNBOOK.md) for the complete daily workflow.

## Memory and repository structure

```text
config/                       Topic weights, sources, policy and identity aliases
schemas/                      JSON Schema 2020-12 for stories, tools and configs
radar/                        Offline validation, dedupe and rollup CLI
tests/                        Behavioral tests and CLI integration checks
data/seen-items.jsonl          Append-only story/event history
data/publications.jsonl        Explicitly reviewed public editorial records
data/tools.jsonl               Stable tool registry
data/tool-observations.jsonl   Append-only dated evaluation/measurement history
data/rollup-state.json         Explicit coverage cutoff for reproducible views
data/rollups/{weekly,monthly}/ Derived JSON counts and historical tool state
reports/YYYY/YYYY-MM-DD.md     Original daily report path
reports/weekly/YYYY/           Generated ISO-week Markdown reports
reports/monthly/YYYY/          Generated calendar-month Markdown reports
templates/                    Daily, weekly, monthly and JSON record templates
docs/                         Architecture, dedupe, data contracts and operations
.github/                      Validation workflow, PR template and Actions updates
web/                          Static design assets, standalone export check and Pages bootstrap
```

## What the system enforces

- Real dates, strict fields/types, unique IDs/tags, finite numbers and valid URLs.
- Topic weights totaling 100 and duplicate-key rejection for YAML and JSON.
- Report paths/dates, v2 item markers, tool references and prior update lineage.
- Semantic identity across product aliases; similarity only requests review.
- Primary evidence and distinct developments for material updates.
- Explicit review rationale before publishing ambiguous v2 stories.
- Append-only story/observation history checked against the prior Git revision.
- Weekly/monthly output drift checks, with hash-locked Python dependencies and
  commit-pinned GitHub Actions on Linux and Windows.

## Identity and material updates

Identity is `productKey + eventKey + version + milestone`, not the headline.
`status` remains the product lifecycle (GA, RC, Preview, etc.);
`coverage` separately describes `NEW` or `UPDATE`.

A new milestone/capability gets a new immutable ID, `updateOf`, a change summary
and primary evidence. Historical rows are preserved. Ambiguous paraphrases,
cross-language wording without explicit shared keys and overloaded source URLs
are routed to review; deterministic matching is not an embedding model.

Read [DEDUPE.md](docs/DEDUPE.md) and [DATA-CONTRACTS.md](docs/DATA-CONTRACTS.md).

## Historical trends and limitations

Rollups count recorded unique events, compare equal elapsed calendar days and
show latest tool state as of the cutoff. Missing/zero growth baselines are N/A.
Stars/forks are optional measurements, not adoption evidence. Old observation
dates stay visible, so an unchanged verdict is not presented as a fresh review.

The nine seed stories and the original baseline report are retained. Four tools
are cataloged from that baseline; only C# Dev Kit has an initial observation,
copied from its historical Preview/Try verdict. No stars or release facts are
invented. Legacy records remain unchanged. Six stories were separately rechecked
against primary sources on 2026-10-10 and curated into public Thai articles; the
remaining legacy stories are not published on the website.

`config/radar.yml` describes the intended daily 08:30 Asia/Bangkok schedule.
This repository provides offline memory utilities and CI validation. The external
discovery/reporting job must follow the runbook; this change does not install or
modify that scheduler. CI validates memory and builds the reviewed public site.
Cross-repository auto-publication activates only after the owner configures its
scoped token and `WEB_PUBLISH_ENABLED` variable.

## Website and distribution

```console
python -m radar.site --output dist
python web/check_site.py dist
python -m http.server --directory dist
python -m radar.notifications --date 2026-10-10 --output work/teams-card.json
```

The site includes readable article pages, references, text/tag search, topic and
verdict filters, coverage weights, public weekly/monthly digests, RSS and a JSON
feed. It uses plain HTML/CSS/JavaScript and the existing Python runtime, with no
additional dependencies. Builds refuse non-empty output directories; review or
choose a fresh directory before rebuilding. See [WEB-PUBLICATION.md](docs/WEB-PUBLICATION.md).

Teams Workflows group-chat cards and generic JSON webhooks use explicit opt-in
delivery; dry runs do not read destination secrets or contact services. Multiple
destinations are selected by repeating `--destination-env`. RSS is also a public
subscription channel. See [NOTIFICATIONS.md](docs/NOTIFICATIONS.md).

Vector search remains an optional future index. Current text/tag search is local;
structured event identity remains the authority for dedupe. See [SEARCH.md](docs/SEARCH.md).

## Contributing and license

Read [CONTRIBUTING.md](CONTRIBUTING.md). Licensed under [Apache-2.0](LICENSE).
