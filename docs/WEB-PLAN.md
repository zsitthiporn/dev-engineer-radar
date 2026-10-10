# Public reading experience and delivery plan

User-approved scope: a clean Thai engineering publication on GitHub Pages, a separate public `zsitthiporn/dev-engineer-radar-web` repository for GitHub Free, private intelligence storage, and Teams group-chat delivery via Workflows. No new dependencies.

1. Recheck primary sources and curate explicit public records; preserve legacy history.
2. Add strict publication schema, static rendering, responsive reading/search/coverage/archive views, RSS and JSON feeds. Export only projected approved content.
3. Add dry-run-first Teams/JSON webhook adapters and manual delivery workflows. Configure real destinations only through owner-managed GitHub Secrets.
4. Validate/tests/build in private CI; publish only generated site files across repositories with a narrowly scoped owner-managed token. Public CI verifies checksums and deploys Pages.
5. Verify desktop/mobile, public path handling, privacy boundary and payload behavior; focused adversarial review; commit to main in coherent groups; verify remote CI and deployed website.

Vector search is deferred: current six curated articles fit local text/tag search. Later index public article chunks, attach source/article IDs and dates, and evaluate relevance against a labeled query set. Embedding matches may suggest duplicate review; they never erase event history or replace structured identity.

Live dependencies: owner sets Pages source to GitHub Actions, cross-repository publication token and Teams Workflows group-chat destination. Do not fabricate a configured collector or a successful live notification.
