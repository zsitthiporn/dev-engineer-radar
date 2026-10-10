"""Publish an already validated public site tree, preserving public repository infrastructure."""
import argparse
import json
import os
import sys
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from radar.notifications import NoRedirect
from web.check_site import check_site

TARGET = "zsitthiporn/dev-engineer-radar-web"


def publish(directory, token):
    check_site(directory)
    if not token:
        raise ValueError("WEB_PUBLISH_TOKEN is missing; configure the scoped public-repo token")
    if not isinstance(token, str) or not token.isascii() or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in token):
        raise ValueError("WEB_PUBLISH_TOKEN is malformed; re-enter it directly in GitHub Secrets")
    opener = build_opener(NoRedirect())

    def api(path, body=None, method=None):
        url = "https://api.github.com/repos/" + TARGET + "/" + path
        try:
            request = Request(url, data=json.dumps(body).encode() if body is not None else None,
                              headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                                       "Content-Type": "application/json", "X-GitHub-Api-Version": "2022-11-28"}, method=method)
            with opener.open(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            raise ValueError(f"public repository operation rejected (HTTP {exc.code})") from None
        except (URLError, OSError, TimeoutError, HTTPException, UnicodeError, ValueError):
            raise ValueError("public repository request failed; inspect public branch before retrying") from None

    head = api("git/ref/heads/main")["object"]["sha"]
    parent = api("git/commits/" + head)
    elements = [{"path": p.relative_to(directory).as_posix(), "mode": "100644", "type": "blob",
                 "content": p.read_text(encoding="utf-8")} for p in sorted(directory.rglob("*")) if p.is_file()]
    site_tree = api("git/trees", {"tree": elements})["sha"]
    old_tree = api("git/trees/" + parent["tree"]["sha"])
    if any(r["path"] == "site" and r["sha"] == site_tree for r in old_tree["tree"]):
        print("Public site unchanged; no commit required")
        return
    # Replace only site/; stale articles disappear without copying/removing other root paths.
    tree = api("git/trees", {"base_tree": parent["tree"]["sha"], "tree": [
        {"path": "site", "mode": "040000", "type": "tree", "sha": site_tree}]})["sha"]
    commit = api("git/commits", {"message": "publish: refresh curated public engineering radar", "tree": tree, "parents": [head]})["sha"]
    # Non-forced sibling updates reject concurrent changes rather than overwrite them.
    api("git/refs/heads/main", {"sha": commit, "force": False}, "PATCH")
    print(f"Public site published: {commit}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    try:
        publish(args.directory.resolve(), os.environ.get("WEB_PUBLISH_TOKEN"))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(f"Publication failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
