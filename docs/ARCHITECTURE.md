# Architecture

## Purpose

Dev Engineer Radar is a persistent personal engineering intelligence system. The repository is not only an archive of daily news; it is the memory layer used to avoid repetition and track technology evolution over time.

## Pipeline

```text
Recent sources
    ↓
Candidate discovery
    ↓
Primary-source verification
    ↓
Semantic normalization
    ↓
Persistent dedupe against data/seen-items.jsonl
    ↓
Material-update detection
    ↓
Ranking
    ↓
Daily report
    ↓
Append seen history
```

## Candidate identity

A candidate must be normalized to a stable semantic identity before ranking.

Recommended components:

- product or project
- feature, release, capability or event
- version or lifecycle milestone when meaningful

Examples:

```text
github-copilot-local-sandbox-ga
kubernetes-cgroup-v2-failcgroupv1-default-v1-35
csharp-dev-kit-11-performance-rearchitecture
```

Do not derive identity from article titles. Two different articles about the same event must resolve to the same identity.

## Seen history

`data/seen-items.jsonl` is append-oriented JSON Lines. Each line is one canonical story record.

Minimum record shape:

```json
{
  "id": "github-copilot-local-sandbox-ga",
  "product": "GitHub Copilot",
  "event": "Local Sandboxing GA",
  "firstSeen": "2026-10-10",
  "lastReported": "2026-10-10",
  "status": "GA",
  "tags": ["AI", "DevTool", "Security"],
  "sourceType": "official",
  "sourceUrl": "https://example.com"
}
```

Optional fields may include `version`, `maturity`, `recommendation`, `updateOf`, `changeSummary` and `reportPath`.

## Update rule

Previously seen stories are skipped by default. A story may return only if there is a material new development.

When it returns:

- keep the original semantic lineage
- label the report item `UPDATE`
- explain exactly what changed
- update `lastReported`
- use `updateOf` when a new semantic id is needed for a new milestone

## Ranking

Candidate ranking considers:

1. Impact
2. Practical usefulness
3. Novelty
4. Credibility
5. Relevance to tracked stack

High-priority stack relevance includes .NET/backend and Kubernetes/DevOps topics defined in `config/topics.yml`.

## Repository write discipline

- One daily report per date.
- Avoid rewriting historical reports except to fix factual errors.
- Append canonical story records only after the story is actually included in a report.
- Prefer primary sources in persistent records.
- Keep generated state machine-readable.

## Future extensions

Possible additions without changing the core model:

- weekly and monthly rollups
- trend scoring by tag and project
- adoption/watch/skip lifecycle tracking
- GitHub Actions validation for JSONL/YAML
- dashboard generation
- searchable static site
- embeddings or external database if the corpus becomes large
