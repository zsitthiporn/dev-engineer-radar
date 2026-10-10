# Architecture

Modified 2026-10-10: schemas, conservative identity matching and derived history views.

## Purpose and boundary

Dev Engineer Radar uses GitHub as durable, reviewable memory. Human/agent producers
discover developments, verify primary sources and write Thai editorial reports.
The Python package validates the memory, classifies candidates and derives views
offline. It does not crawl news, fetch metrics or call an LLM.

## Pipeline

```text
primary sources -> verified candidate -> normalized product/event keys
                                      -> dedupe against ALL history
                                         DUPLICATE -> omit
                                         REVIEW -> inspect evidence; record rationale
                                         NEW / UPDATE -> rank and report
                                      -> append story and tool observations
                                      -> validate + rebuild rollups + tests
                                      -> one atomic Git publication
```

Ranking and freshness are editorial policies in config/radar.yml and
config/topics.yml. The CLI does not assign credibility scores or infer maturity.
Source verification remains a producer responsibility: schema validation cannot
prove a URL's claims are true.

## Store ownership

| Store | Identity and responsibility |
|---|---|
| seen-items.jsonl | Immutable event ID; firstSeen/lastReported belong to this event |
| tools.jsonl | Stable tool ID and discoverability metadata; metadata may be corrected |
| tool-observations.jsonl | Immutable observation ID; one row per tool/day, chronological per tool |
| daily Markdown | Coverage evidence; v2 stories require an exact item marker |
| rollup-state.json | Explicit asOf cutoff; checked derived output uses it |
| rollup JSON/Markdown | Rebuildable views; never manually edit generated content |

New material updates append a NEW ID and link to an earlier parent via updateOf.
Parents must precede children and belong to the same canonical product. Preserve
both the parent's lastReported and the old report. The earlier design's suggestion
to update lastReported in place is superseded by immutable event rows.

## Backward compatibility

All nine original records remain byte-for-byte intact. The legacy schema branch
permits their IDs and original field names; new IDs require schemaVersion 2.
The old status field continues to mean lifecycle, including Available/Upcoming.
coverage is a separate v2 enum. No new maturity/recommendation is inferred from an
old lifecycle label.

The initial C# Dev Kit observation copies the seed report's explicit Preview/Try
editorial verdict and states its provenance. The other catalog tools have unknown
state until a real observation is appended. No collector success or adoption
measurement is implied by baseline imports.

## Dedupe and review

Exact identity wins before fuzzy matching or update lineage. Product aliases are
curated, never substring matches. Event keys must name the capability, not a
paraphrased headline. An identical source URL alone requests review because one
release note can describe multiple capabilities. Similarity is deterministic and
used only to locate likely matches for a producer to inspect.

Repository validation re-runs dedupe for v2 rows against earlier history. Exact
duplicates fail; ambiguous NEW records require a dedupeReview linked to the
matched ID. UPDATE additionally requires primary evidence, materialChange and a
distinct structured identity. See [DEDUPE.md](DEDUPE.md).

## Rollups

Weekly boundaries follow ISO week-year; monthly boundaries follow calendar
months. Daily date fields are Asia/Bangkok calendar dates. Periods are clipped at
asOf, and comparisons use the same elapsed day count, capped at the previous
period's length. A month is computed directly from event rows, never by adding
weeks that cross month boundaries.

Each event contributes once to its product and tags. Tool state uses the most
recent observation at or before period end. Future rows are ignored. Optional
star deltas require measurements on both sides. A zero denominator yields null
in JSON and N/A in prose. Missing metrics stay unknown.

Counts measure repository coverage, not market adoption or popularity. A day
without events may mean no collection run. No assertion of complete collection
is made. Pure generated counts and separately authored editorial commentary use
different paths so regeneration does not overwrite editorial reasoning.

## Validation and publication

Validation is read-only. JSON/YAML duplicate keys, invalid schema types/dates,
non-finite values, missing references, ambiguous aliases and history violations
fail with context. The whole root is validated before rollup generation writes
any files. Rollup check compares exact deterministic output and reports stale or
unexpected artifacts; it never deletes files.

Publish report + history + observations + rollups in one Git commit. Multiple
file writes in a local checkout are not a transaction; the Git commit is the
publication unit. A producer must inspect/refetch a moved main head and re-run
dedupe before retrying. Never force push or overwrite concurrent data.

CI uses contents:read, disabled persisted checkout credentials, full Git history,
hash-locked packages and SHA-pinned actions. It checks Linux/Python 3.12 and 3.13
and Windows/Python 3.12. It has no scheduler, repository-write step or secrets.

## Scaling

History is scanned in memory with deterministic comparisons. That is appropriate
for a personal corpus; large-scale indexing, embeddings, a database and a UI are
future choices requiring measured need. This upgrade adds no paid services or
production infrastructure.
