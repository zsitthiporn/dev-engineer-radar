"""Explicit, dry-run-first fan-out of public articles to Teams Workflows or JSON webhooks."""
import argparse
import hashlib
import ipaddress
import json
import os
import re
import socket
import sys
import unicodedata
from http.client import HTTPException
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
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


def card_text(value, limit=None):
    """Plain editorial text inside Teams' limited Markdown dialect."""
    value = " ".join(value.split())
    if limit and len(value) > limit:
        end = limit - 1
        # Avoid separating a Thai base letter from its following vowel/tone marks.
        while end and unicodedata.category(value[end]).startswith("M"):
            end -= 1
        value = value[:end].rstrip() + "…"
    return re.sub(r"([\\`*_\[\]()!<>])", r"\\\1", value)


def teams_payload(row):
    counts = " · ".join(f"{label} {sum(i['recommendation'] == label for i in row['items'])}"
                        for label in ("Try", "Watch", "Skip")
                        if any(i["recommendation"] == label for i in row["items"]))
    body = [{"type": "Container", "style": "emphasis", "bleed": True, "items": [
        {"type": "TextBlock", "text": "ENGINEERING BRIEF", "size": "Small",
         "weight": "Bolder", "color": "Accent", "wrap": True},
        {"type": "TextBlock", "text": row["title"], "size": "Large",
         "weight": "Bolder", "spacing": "Small", "wrap": True},
        {"type": "TextBlock", "text": f"{row['date']}  /  {len(row['items'])} ข่าวคัดแล้ว",
         "size": "Small", "isSubtle": True, "spacing": "Small", "wrap": True},
        {"type": "TextBlock", "text": counts or "ยังไม่มีข่าวในฉบับนี้",
         "size": "Small", "spacing": "Small", "wrap": True}]}]
    for index, item in enumerate(row["items"], 1):
        verdict = item["recommendation"]
        # Encode Markdown delimiters without changing the generic digest's URL.
        link = urlsplit(item["url"])
        link = link._replace(path=quote(link.path, safe="/%:@!$&'*+,-.;=~"),
                             query=quote(link.query, safe="%:@!$&'*+,-.;=/?~"),
                             fragment=quote(link.fragment, safe="%:@!$&'*+,-.;=/?~")).geturl()
        body.append({"type": "Container", "separator": True, "spacing": "Medium", "items": [
            {"type": "ColumnSet", "columns": [
                {"type": "Column", "width": "stretch", "items": [
                    {"type": "TextBlock", "text": f"[{index:02d} · {card_text(item['title'])}]({link})",
                     "weight": "Bolder", "wrap": True, "maxLines": 2}]},
                {"type": "Column", "width": "auto", "spacing": "Small", "items": [
                    {"type": "TextBlock", "text": verdict, "size": "Small", "weight": "Bolder",
                     "color": {"Try": "Good", "Watch": "Warning", "Skip": "Default"}[verdict]}]}]},
            {"type": "TextBlock", "text": card_text(item["summary"], 140), "wrap": True,
             "maxLines": 2, "size": "Small", "spacing": "Small"}]})
    body.append({"type": "TextBlock", "text": "แตะหัวข้อเพื่ออ่านต่อ · รายละเอียดและ primary sources อยู่บนเว็บ",
                 "size": "Small", "isSubtle": True, "wrap": True, "separator": True, "spacing": "Medium"})
    return {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive",
            "contentUrl": None, "content": {"$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard", "version": "1.2", "body": body,
            "msteams": {"width": "Full"},
            "speak": f"Dev Engineer Radar ฉบับ {row['date']} มี {len(row['items'])} ข่าว {counts}",
            "fallbackText": f"{row['title']} · {row['date']} · {len(row['items'])} ข่าว\n{row['url']}\n{row['deliveryId']}",
            "actions": [{"type": "Action.OpenUrl", "title": "อ่านข่าวทั้งหมดบน Radar →", "url": row["url"]}]}}]}


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
