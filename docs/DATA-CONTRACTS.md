# Data contracts

Schemas are JSON Schema 2020-12 with format checks enabled. Unknown fields fail.
JSONL is UTF-8, one JSON object per line, with no blank lines, duplicate keys or
NaN/Infinity. Empty observation stores are valid. YAML uses a safe loader with
duplicate-key rejection; quote dates if future config fields need string dates.

## Story rows

The nine original IDs are grandfathered by the legacy branch. New events use
schemaVersion 2; start from templates/story.json.

Required fields include id, product, productKey, event, eventKey, milestone,
publishedAt, firstSeen, lastReported, status, coverage, tags, sourceType,
sourceUrl, reportPath and evidenceSummary.

- Dates are YYYY-MM-DD calendar dates in Asia/Bangkok; publishedAt <= firstSeen
  <= lastReported. Use the source's publication date, not a search crawl date.
- status is a nonempty product lifecycle label; coverage is NEW or UPDATE.
- maturity, if recorded, is Experimental, Preview or Production Ready.
- recommendation, if recorded, is Try, Watch or Skip.
- score, if recorded, is finite and in 0..10; ranking remains editorial.
- reportPath must exist, match lastReported and use reports/YYYY/YYYY-MM-DD.md.
- Reports for v2 rows contain `<!-- radar:item CANONICAL-ID -->`.
- toolIds, if present, must reference data/tools.jsonl.
- UPDATE requires an earlier same-product updateOf, materialChange,
  changeSummary and primary evidence. NEW cannot carry update fields.
- REVIEW resolution for an independent NEW event requires dedupeReview with
  matchedId, reason and reviewedAt no later than lastReported.

An event's date is not its product's first discovery date. Each material update
is a separate immutable event, so do not overwrite the parent's lastReported.
sourceType is official, repository, documentation or community; community-only
material updates fail. Source authenticity remains a producer verification task.

## Tool registry

schemaVersion 1, stable id, name, aliases, homepage, tags and firstSeen are
required. repositoryUrl is optional. Use templates/tool.json.

IDs are foreign keys: never rename or reuse an ID. Changing homepage or adding
aliases is a metadata correction, not an observation. Tool catalog membership
does not imply endorsement, maturity or an up-to-date evaluation.

## Tool observations

schemaVersion 1, unique id, toolId, observedAt, recommendation, maturity,
sourceUrl, notes and storyIds are required. storyIds may be empty for an
independent evaluation. Source evidence and evaluation rationale must be explicit.

At most one observation per tool/day, appended in ascending date order per tool.
observedAt cannot predate the tool or its linked stories. metrics may contain
nonnegative integer stars and forks. Omit unmeasured metrics; do not fill them
with zero. When collecting metrics, cite the corresponding repository/API snapshot
in sourceUrl and describe the measurement in notes.

The first seed observation copies only the historical C# Dev Kit verdict; it
contains no measurements. Subsequent observations capture actual lifecycle changes.

## Derived views

data/rollup-state.json records schemaVersion 1 and an explicit asOf cutoff.
Weekly JSON files use ISO YYYY-Www; monthly files use YYYY-MM. Each view includes
period bounds, comparison bounds, partial status, counts, product/tag deltas,
latest dated tool state and linked event evidence. JSON null means unavailable
growth/measurement, not zero.

Regenerate with the same asOf to reproduce byte-identical output. CI checks
content against the raw stores. Unexpected derived files are reported and not
deleted automatically. Editorial templates belong in separately authored notes,
not generated output paths.

## Compatibility and correction

The original daily report and story rows are retained unchanged. Schema versions
make additions explicit. Unknown future versions fail instead of being accepted
silently. Normal CI enforces the prefix of historical rows against the base
commit. Factual corrections must use a reviewed subsequent record/report; rewriting
existing rows needs a separately approved maintenance workflow.
