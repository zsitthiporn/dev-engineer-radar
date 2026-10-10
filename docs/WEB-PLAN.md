# Public reading experience and delivery plan

Current owner-approved scope: a public `zsitthiporn/dev-engineer-radar` repository,
GitHub Pages from that same repository, curated Thai articles and Teams group-chat
delivery via Workflows. No new dependencies. Repository/history visibility is public;
website projection remains an editorial selection, not a repository privacy control.

1. Preserve original reports/history and curate explicit source-checked articles.
2. Keep strict schemas, responsive reading/search/coverage/archive, RSS/JSON feeds.
3. Use dry-run-first Teams/JSON delivery with owner-managed GitHub Secrets.
4. Build/test/validate on PRs and main; deploy only verified `dist/` from public main
   through the `github-pages` environment and GitHub's built-in authentication.
5. Verify new destination links, export boundaries, workflow permission/branch guards,
   tests and deployed website; review the migration; commit orderly changes to main.

The separate web repository, cross-repository publisher/token and its Pages bootstrap
are no longer part of production. The owner changes source visibility and chooses
Pages Source → GitHub Actions. Retired repository files remain untouched.

Vector search is deferred: six curated articles fit local text/tag search. A later
index should retain article/source IDs and dates, with evaluated relevance. Embeddings
may suggest review but cannot erase event history or replace structured identity.

Teams still requires owner configuration and a deliberate test send. No collector
or external ChatGPT schedule is installed or changed by the publication workflow.
