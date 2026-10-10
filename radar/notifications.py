"""Explicit, dry-run-first fan-out of public articles to Teams Workflows or JSON webhooks."""
import argparse
import hashlib
import ipaddress
import json
import os
import re
import socket
import sys
from http.client import HTTPException
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

from radar.site import DEFAULT_URL, publications, public_url


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def digest(root, day, site_url=DEFAULT_URL):
    day = date.fromisoformat(day).isoformat()
    site_url = public_url(site_url).rstrip("/") + "/"
    items = [{"id": r["id"], "title": r["title"], "summary": r["summary"],
              "recommendation": r["recommendation"], "references": r["references"],
              "url": site_url + f"articles/{r['id']}/"}
             for r in publications(Path(root)) if r["editionDate"] == day]
    identity = hashlib.sha256(json.dumps({"date": day, "items": items}, ensure_ascii=False,
                                        sort_keys=True).encode()).hexdigest()[:24]
    return {"schemaVersion": 1, "deliveryId": "radar-" + identity, "date": day,
            "title": "Dev Engineer Radar", "url": site_url, "items": items}


def teams_payload(row):
    # Bound summaries and card count; include the full digest identity in the message.
    body = [{"type": "TextBlock", "text": f"Dev Engineer Radar · {row['date']}",
             "weight": "Bolder", "size": "Large", "wrap": True},
            {"type": "TextBlock", "text": f"{len(row['items'])} ข่าวคัดแล้ว · อ่านรายละเอียดและ references บนเว็บ", "wrap": True}]
    for item in row["items"][:5]:
        body.extend([{"type": "TextBlock", "text": item["title"], "weight": "Bolder", "wrap": True},
                     {"type": "TextBlock", "text": item["summary"][:220], "wrap": True},
                     {"type": "TextBlock", "text": item["url"], "wrap": True}])
    body.append({"type": "TextBlock", "text": row["deliveryId"], "isSubtle": True, "size": "Small", "wrap": True})
    return {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive",
            "contentUrl": None, "content": {"$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard", "version": "1.2", "body": body,
            "actions": [{"type": "Action.OpenUrl", "title": "อ่านบน Radar", "url": row["url"]}]}}]}


def validate_destination(value, resolver=socket.getaddrinfo):
    # Webhook query signatures are intentionally allowed here, never in public exports.
    try:
        p = urlsplit(value)
        if (p.scheme != "https" or not p.hostname or p.username or p.password or p.fragment
                or p.port not in (None, 443) or not value.isascii()
                or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)):
            raise ValueError
        addresses = resolver(p.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError
    except (ValueError, TypeError, OSError):
        raise ValueError("webhook destination must resolve to public HTTPS") from None
    return value


def send(value, payload, opener=None):
    validate_destination(value)
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if len(encoded) > 24_000:
        raise ValueError("notification exceeds conservative 24 KB payload budget")
    try:
        request = Request(value, data=encoded, headers={"Content-Type": "application/json"}, method="POST")
        # Never retry ambiguous POST outcomes: a timeout may have delivered the card.
        with (opener or build_opener(NoRedirect())).open(request, timeout=20) as response:
            if not 200 <= response.status < 300:
                raise ValueError("webhook did not acknowledge delivery")
    except HTTPError as exc:
        raise ValueError(f"webhook rejected request (HTTP {exc.code}); inspect destination privately") from None
    except (URLError, OSError, TimeoutError, HTTPException, UnicodeError, ValueError):
        raise ValueError("webhook delivery uncertain; check destination before rerunning") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--date", required=True)
    parser.add_argument("--site-url", default=DEFAULT_URL)
    parser.add_argument("--adapter", choices=["teams", "json"], default="teams")
    parser.add_argument("--output", type=Path, help="save a public-only payload for review")
    parser.add_argument("--send", action="store_true", help="explicitly send to every named environment variable")
    parser.add_argument("--destination-env", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        row = digest(args.root, args.date, args.site_url)
        payload = teams_payload(row) if args.adapter == "teams" else row
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        if args.send:
            if not args.destination_env or len(set(args.destination_env)) != len(args.destination_env):
                raise ValueError("send requires distinct, explicitly selected destination environment names")
            destinations = []
            for name in args.destination_env:
                if not re.fullmatch(r"RADAR_[A-Z0-9_]+_WEBHOOK", name):
                    raise ValueError("destination names must use RADAR_*_WEBHOOK")
                value = os.environ.get(name)
                if not value:
                    raise ValueError(f"destination secret missing: {name}")
                validate_destination(value)
                destinations.append((name, value))
            # Preflight all destinations before delivering to any of them.
            if not row["items"]:
                print("No public articles for date; nothing sent")
                return 0
            for name, value in destinations:
                send(value, payload)
                print(f"Acknowledged: {name}; {row['deliveryId']}")
        else:
            print(f"Dry run: {len(row['items'])} public articles; {row['deliveryId']}; no network requests")
        return 0
    except (ValueError, OSError) as exc:
        print(f"Notification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
