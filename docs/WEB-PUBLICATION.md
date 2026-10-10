# Private intelligence, public publication

GitHub Free supports Pages from public repositories. The owner explicitly approved
`zsitthiporn/dev-engineer-radar-web` as a separate public destination. The source
repository remains private. Upgrading to Pro is not required for this split.

## Content contract

`data/publications.jsonl` is the explicit publication allowlist. Each row conforms
to `schemas/publication.schema.json`, refers to an existing story ID and retains
its primary source. It contains original Thai summaries, factual/analysis/action
sections, recommendations and reference links. No raw report Markdown is rendered.

- `publishedAt`: date of the primary article/release.
- `editionDate`: immutable date first included in a public Radar edition; public
  ISO-week/month digests and notification selection use this date.
- `reviewedAt`: latest source/editorial verification date, visible on article pages.
- Material developments retain the underlying new story ID/update lineage. Small
  editorial corrections may amend the publication row but do not move its edition.

The initial six sources were read on 2026-10-10: GitHub local sandbox GA and Ollama
discovery, Docker Cloud Sandboxes, Kubernetes cgroup v2 and Node Swap, Microsoft
C# Dev Kit 11. The nine original history rows/report remain untouched. Docker's
primary article is dated October 1: its inclusion is a baseline follow-up, not a
claim that it occurred in the latest 72 hours. Three other legacy stories remain
private because no public editorial review was performed for them.

## Build and privacy boundary

`python -m radar.site --output dist` validates private memory, validates every public
record, then constructs only projected public fields and known static assets.
It never copies repository folders. Unknown publication fields, signed query URLs,
credentials in source URLs, duplicate IDs or missing primary references fail.
HTML is escaped; JavaScript only filters existing DOM cards. No analytics, cookies,
external fonts, frontend credentials or remote search calls are included.

`web/check_site.py dist` checks exact allowed paths, SHA-256/byte counts, symlinks,
relative links and local fragments. `dist/` is ignored. Output must be empty to
prevent accidental stale/private files. Tests include an internal canary which
must not appear in any export. This is an enforced structural boundary, not an
automatic classifier of sensitive prose: the editor must review content.

## GitHub Actions and publication

Private workflows:

1. `validate.yml`: Linux/Python 3.12 & 3.13 and Windows/Python 3.12 validate memory,
   append-only history, tests, derived rollups and public builds.
2. `publish-web.yml`: builds/checks a public artifact on PRs and main. Main alone
   may sync `site/` into the public repo when `WEB_PUBLISH_ENABLED=true`.
3. `notify.yml`: manual dry-run default; sending is an explicit input on main.

Public `.github/workflows/pages.yml` validates only `site/`, uploads that directory
and deploys via OIDC to `github-pages`. Only its deploy job has Pages write/id-token
permissions. Actions are pinned to inspected commit SHAs. The public repository
does not check out this private repository. Public builds use Python stdlib only.

## One-time owner configuration

In the public repo, Settings → Pages → Source → GitHub Actions. Initial publication
can be performed through the connected GitHub tool. For ongoing automatic syncing:

1. Create a fine-grained personal access token scoped only to
   `dev-engineer-radar-web`, with **Contents: Read and write**. Set an expiry and
   rotate it. Do not grant access to all repositories.
2. In the private repo, Settings → Secrets and variables → Actions → Secrets,
   create `WEB_PUBLISH_TOKEN`. Enter it directly in GitHub; never paste it into chat.
3. Under Actions Variables create `WEB_PUBLISH_ENABLED` with value `true`.
4. Run **Build and publish public web** once and verify both repositories' runs.

Token creation/entry is left to the owner. Do not treat a missing token as permission
to expose the private repo or broaden credentials. Disabling the variable pauses
syncing; initial public deployment and private validation still work independently.

`radar.publish` validates before network access, writes only a new `site/` tree,
preserves README/.github/other root paths and replaces stale site files atomically.
An unchanged site tree creates no commit. The final ref update is non-forced and
has the observed main commit as parent: a concurrent sibling update is rejected.
Failures do not print tokens, HTTP bodies or signed URLs. Review the current public
head before retrying a failed publication.

## Daily producer integration

The existing external discovery job must append history/report/observations, rebuild
rollups, then curate a schema-valid publication row with current primary evidence.
Commit that set to main; CI builds/syncs/deploys once auto-publication is configured.
No collector or ChatGPT schedule is installed/changed by these workflows. The site
labels its latest reviewed date rather than promising that collection ran today.

After confirming the site is live, an authorized producer may explicitly invoke
the notification workflow for the public edition. News collection, editorial
approval, site deployment and destination delivery are separate checkpoints.

## References

- [GitHub Pages availability](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)
- [Custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
