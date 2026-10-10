"""Standalone stdlib check copied into the public deploy repository."""
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

FIXED = {"index.html", "404.html", "coverage/index.html", "archive/index.html", "assets/style.css",
         "assets/app.js", "assets/mark.svg", "feed.json", "feed.xml", "sitemap.xml", "robots.txt", ".nojekyll"}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []
        self.ids = set()
        self.fragments = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if "id" in data:
            if data["id"] in self.ids:
                raise ValueError("duplicate HTML ID")
            self.ids.add(data["id"])
        for key in ("href", "src"):
            value = data.get(key, "")
            if not value:
                continue
            p = urlsplit(value)
            if p.scheme and p.scheme != "https":
                raise ValueError("unsafe link scheme")
            if not p.scheme and p.netloc:
                raise ValueError("protocol-relative URL forbidden")
            if not p.scheme:
                if p.path:
                    self.paths.append(unquote(p.path))
                elif p.fragment:
                    self.fragments.append(p.fragment)


def check_site(root):
    root = Path(root).resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != 1:
        raise ValueError("unsupported site manifest")
    expected = set(manifest["files"])
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != expected | {"manifest.json"}:
        raise ValueError("site must contain exactly manifest files")
    if not FIXED <= expected:
        raise ValueError("required public site file missing")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("symlinks forbidden")
    for relative in expected:
        if relative not in FIXED and not re.fullmatch(r"articles/[a-z0-9]+(?:-[a-z0-9]+)*/index\.html", relative):
            raise ValueError("file outside public allowlist")
        file = root / relative
        blob = file.read_bytes()
        meta = manifest["files"][relative]
        if meta != {"sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob)}:
            raise ValueError("site checksum mismatch")
        if relative.endswith(".html"):
            parser = Links()
            parser.feed(blob.decode("utf-8"))
            if not set(parser.fragments) <= parser.ids:
                raise ValueError("broken local fragment")
            for link in parser.paths:
                target = (file.parent / link).resolve()
                if target == root or root in target.parents:
                    target = target / "index.html" if target.is_dir() else target
                    if not target.is_file():
                        raise ValueError("broken local link")
                else:
                    raise ValueError("local link escapes site")
    return len(actual)


if __name__ == "__main__":
    try:
        print(f"Public artifact verified: {check_site(sys.argv[1])} allowlisted files")
    except (ValueError, OSError, KeyError, IndexError) as exc:
        print(f"Public artifact rejected: {exc}", file=sys.stderr)
        raise SystemExit(1)
