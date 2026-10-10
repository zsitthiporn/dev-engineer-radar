# Dev Engineer Radar

Personal engineering intelligence repository for high-signal developer, backend, AI tooling, DevOps and cloud-native updates.

## Goals

- Discover useful new tools before they become mainstream.
- Prioritize practical engineering impact over general tech news.
- Keep daily reports concise and actionable.
- Prevent repeated coverage of the same underlying story.
- Build a searchable long-term history of tools, releases and engineering trends.

## Coverage

Primary focus:

- AI developer tools, coding agents, MCP, CLI tools and agent runtimes
- Kubernetes, K3s, Argo CD, Helm, Docker, GitOps and platform engineering
- C#, .NET, ASP.NET Core, Web API, gRPC, EF Core and SQL Server
- Git, GitHub, GitLab, CI/CD and observability
- Infrastructure, architecture, security and databases

## Repository structure

```text
.
├── config/
│   ├── topics.yml          # Topic weights and tracked technologies
│   └── radar.yml           # Selection, freshness and dedupe policy
├── data/
│   └── seen-items.jsonl    # Persistent semantic history for deduplication
├── docs/
│   └── ARCHITECTURE.md     # Radar workflow and data model
├── reports/
│   └── YYYY/
│       └── YYYY-MM-DD.md   # Daily radar reports
├── templates/
│   └── daily-report.md     # Canonical report shape
└── README.md
```

## Dedupe model

Each reported story gets a semantic identity based on:

```text
product/project + event/feature + version/milestone
```

Example:

```text
github-copilot-local-sandbox-ga
```

A story is not repeated unless there is a material development such as GA/RC, a breaking change, security issue, new benchmark, major adoption, official clarification or a newly available capability. Returning stories are labeled `UPDATE` and must state what changed.

## Daily workflow

1. Discover candidate developments from recent primary sources.
2. Normalize each candidate into a semantic story identity.
3. Check `data/seen-items.jsonl`.
4. Drop duplicates without material changes.
5. Rank remaining stories by impact, usefulness, novelty, credibility and stack relevance.
6. Write the daily report under `reports/YYYY/YYYY-MM-DD.md`.
7. Append reported semantic identities to `data/seen-items.jsonl`.

## Source policy

Prefer primary sources: official release notes, engineering blogs, project repositories, Microsoft/.NET sources, Kubernetes/CNCF sources and official documentation. Community sources may be used for discovery, but important claims should be verified against primary sources.

## Report language

Reports are written in Thai while keeping product names and technical terminology in English.
