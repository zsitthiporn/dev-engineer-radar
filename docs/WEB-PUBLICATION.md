# Single-repository publication

The owner chose a public `zsitthiporn/dev-engineer-radar` repository with GitHub
Pages deployed from this same repository. GitHub Free supports Pages for public
repositories. The reading URL is https://zsitthiporn.github.io/dev-engineer-radar/.
All committed repository files, Git history and Actions logs are public once the
owner changes visibility. Editorial projection controls what the website presents;
it does not make unpublished records private in a public repository.

## Content contract

`data/publications.jsonl` is the explicit website publication allowlist. Each row
conforms to `schemas/publication.schema.json`, refers to an existing story ID and
retains its primary source. It contains original Thai summaries, factual/analysis/
action sections, recommendations and references. Raw report Markdown is not rendered.

- `publishedAt`: date of the primary article/release.
- `editionDate`: immutable date first included in a public Radar edition; public
  ISO-week/month digests and notification selection use this date.
- `reviewedAt`: latest source/editorial verification date, visible on article pages.
- Material developments retain the underlying new story ID/update lineage. Small
  editorial corrections may amend a publication row but do not move its edition.

Six initial sources were read on 2026-10-10: GitHub local sandbox GA and Ollama
discovery, Docker Cloud Sandboxes, Kubernetes cgroup v2 and Node Swap, Microsoft
C# Dev Kit 11. The nine original history rows/report remain unchanged. Docker's
primary article is dated October 1: this is a baseline follow-up, not a claim of
news within 72 hours. Three other legacy stories have no reviewed website article;
their source records are still readable in the public repository.

## Build and editorial boundary

`python -m radar.site --output dist` validates repository memory and every public
record, then constructs projected fields and known static assets only. It does
not copy repository folders. Unknown fields, signed query URLs, credentials in
source URLs, duplicate IDs or missing primary references fail. HTML is escaped;
JavaScript filters existing DOM cards. No tracking, frontend secrets, external
fonts or remote search calls are included.

`web/check_site.py dist` checks exact allowed paths, SHA-256/byte counts, symlinks,
relative links and fragments. `dist/` is ignored and output must be empty. Tests
include a canary excluded from the export. This enforces an editorial/structural
boundary; it is not an automatic sensitive-prose classifier.

## GitHub Actions

1. `validate.yml`: Linux/Python 3.12 and 3.13, Windows/Python 3.12 validate memory,
   append-only history, tests, derived rollups and public builds.
2. `publish-web.yml`: build/test/check on PRs and main. After a successful build,
   only public-repository main runs upload `dist/` as the Pages artifact and deploy
   through the `github-pages` environment. PRs and private-repository runs build
   reviewable artifacts without deploying.
3. `notify.yml`: manual dry-run default; sending is an explicit input on main.

Only the deploy job receives `pages: write` and `id-token: write`. The build has
read-only contents permission and no destination credentials. Actions remain pinned
to commit SHAs. The deployed artifact is `dist/`, never the repository root. Pages
uses GitHub's built-in authentication; no personal access token is needed.

## One-time owner configuration

1. Make `dev-engineer-radar` public after reviewing its repository contents and
   history. The owner performs the visibility change.
2. In this repository, Settings → Pages → Build and deployment → Source →
   **GitHub Actions**.
3. Run **Build and publish public web** from main. Verify both build and deploy,
   then open the reading URL and a full article with references.

The deploy guard deliberately skips private repositories. Changing visibility or
Pages settings alone does not build the site: run the workflow once after setup.
Later relevant pushes to main build/deploy automatically.

## Migration from the separate web repository

The `dev-engineer-radar-web` destination is retired from this producer workflow.
Cross-repository sync, its CLI/tests and the old Pages bootstrap are removed.
`WEB_PUBLISH_TOKEN` and `WEB_PUBLISH_ENABLED` are unused. The owner may remove the
unused secret/variable and revoke the old token in GitHub settings; this change
never reads or deletes credentials. Existing retired-repository files/site are
untouched. Repository archival, deletion or redirecting its old URL is a separate
owner decision. Existing RSS subscriptions need the new `feed.xml` URL.

Canonical article URLs, RSS/JSON feeds, sitemap, 404 navigation and future Teams
cards use the new reading destination. The text/tag search and reading design are
unchanged. No original history, reports, observations or rollups are changed.

## Daily producer integration

The external discovery job must append history/report/observations, regenerate
rollups, then curate a schema-valid website publication row with current primary
evidence. Commit the set to main; CI builds/deploys it after Pages setup. These
workflows do not install/change a news collector or external ChatGPT schedule.
The website shows the latest reviewed date rather than promising daily collection.

After verifying the live edition, an authorized producer may explicitly invoke
the notification workflow. Collection, editorial approval, deployment and delivery
are separate checkpoints. Teams destination credentials stay in GitHub Secrets.

## References

- [GitHub Pages availability](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)
- [Custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
