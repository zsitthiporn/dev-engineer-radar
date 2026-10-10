"""Reproducible ISO-week/calendar-month views of recorded signals."""
import calendar
import json
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from radar.dedupe import product_key
from radar.validation import read_jsonl, read_yaml, validate_repository


def _bounds(kind, period):
    if kind == "weekly" and re.fullmatch(r"\d{4}-W\d{2}", period):
        year, week = map(int, period.replace("W", "").split("-"))
        start = date.fromisocalendar(year, week, 1)
        return start, start + timedelta(days=6), start - timedelta(days=7), start - timedelta(days=1)
    if kind == "monthly" and re.fullmatch(r"\d{4}-\d{2}", period):
        year, month = map(int, period.split("-"))
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        previous_end = start - timedelta(days=1)
        return start, end, previous_end.replace(day=1), previous_end
    raise ValueError("period must be a valid ISO week or calendar month")


def _growth(current, previous):
    return round((current - previous) / previous * 100, 2) if previous else None


def _signals(current, previous):
    return [{"name": key, "count": current[key], "previousCount": previous[key],
             "delta": current[key] - previous[key], "growthPercent": _growth(current[key], previous[key])}
            for key in sorted(current.keys() | previous.keys(), key=lambda k: (-current[k], k))]


def _latest(observations, end):
    result = {}
    for row in sorted(observations, key=lambda r: (r["observedAt"], r["id"])):
        if row["observedAt"] <= end.isoformat():
            result[row["toolId"]] = row
    return result


def build_rollup(stories, tools, observations, kind, period, as_of, config):
    start, full_end, prev_start, prev_full_end = _bounds(kind, period)
    end = min(full_end, as_of)
    if end < start:
        raise ValueError("period begins after as-of date")
    prev_end = min(prev_full_end, prev_start + (end - start))
    current = [r for r in stories if start.isoformat() <= r["lastReported"] <= end.isoformat()]
    previous = [r for r in stories if prev_start.isoformat() <= r["lastReported"] <= prev_end.isoformat()]
    updates = sum(r.get("coverage") == "UPDATE" or bool(r.get("updateOf")) for r in current)
    products = Counter(product_key(r, config) for r in current)
    previous_products = Counter(product_key(r, config) for r in previous)
    tags = Counter(tag for r in current for tag in {t.casefold() for t in r["tags"]})
    previous_tags = Counter(tag for r in previous for tag in {t.casefold() for t in r["tags"]})
    latest, prior = _latest(observations, end), _latest(observations, prev_end)
    tool_rows = []
    for tool in sorted(tools, key=lambda r: r["id"]):
        if tool["firstSeen"] > end.isoformat():
            continue
        observation = latest.get(tool["id"], {})
        earlier = prior.get(tool["id"], {})
        stars = observation.get("metrics", {}).get("stars")
        prev_stars = earlier.get("metrics", {}).get("stars")
        linked_stories = {story_id for o in observations if o["toolId"] == tool["id"]
                          and o["observedAt"] <= end.isoformat() for story_id in o.get("storyIds", [])}
        tool_rows.append({"id":tool["id"], "name":tool["name"],
                          "recommendation":observation.get("recommendation"),
                          "previousRecommendation":earlier.get("recommendation"),
                          "maturity":observation.get("maturity"), "observedAt":observation.get("observedAt"),
                          "stars":stars, "previousStars":prev_stars,
                          "starsDelta":stars - prev_stars if stars is not None and prev_stars is not None else None,
                          "starsGrowthPercent":_growth(stars, prev_stars) if stars is not None and prev_stars is not None else None,
                          "storyCount":sum(tool["id"] in r.get("toolIds", []) or r["id"] in linked_stories for r in current)})
    return {"schemaVersion":1, "kind":kind, "period":period, "asOf":as_of.isoformat(),
            "start":start.isoformat(), "end":end.isoformat(), "fullEnd":full_end.isoformat(),
            "previousStart":prev_start.isoformat(), "previousEnd":prev_end.isoformat(),
            "partial":end < full_end, "comparison":"equal elapsed days, capped by previous period length",
            "counts":{"stories":len(current), "new":len(current)-updates, "updates":updates,
                      "daysWithStories":len({r["lastReported"] for r in current})},
            "products":_signals(products, previous_products), "tags":_signals(tags, previous_tags),
            "tools":tool_rows, "stories":[{"id":r["id"], "product":r["product"], "event":r["event"],
                                          "coverage":"UPDATE" if r.get("coverage") == "UPDATE" or r.get("updateOf") else "NEW",
                                          "sourceUrl":r["sourceUrl"], "reportPath":r["reportPath"]}
                                         for r in sorted(current, key=lambda r: (r["lastReported"], r["id"]))]}


def _cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ").replace("<", "&lt;").replace(">", "&gt;")


def render_rollup(row):
    counts = row["counts"]
    lines = [f"# Dev Engineer Radar — {row['period']}", "",
             f"ช่วงข้อมูล: {row['start']} ถึง {row['end']} (Asia/Bangkok)",
             f"เทียบช่วงก่อน: {row['previousStart']} ถึง {row['previousEnd']}",
             f"สถานะ: {'ยังไม่ครบช่วง' if row['partial'] else 'ครบช่วงตามปฏิทิน'}; snapshot ณ {row['asOf']}", "",
             f"บันทึก {counts['stories']} เหตุการณ์: NEW {counts['new']}, UPDATE {counts['updates']}; "
             f"มี story ใน {counts['daysWithStories']} วัน", "",
             "จำนวนเหล่านี้สะท้อน coverage ใน repo ไม่ใช่ adoption ของอุตสาหกรรม "
             "วันที่ไม่มี story อาจไม่ได้รัน collector และข้อมูลเดิมยังไม่ได้ตรวจข่าวซ้ำในรอบนี้", "",
             "## Product signals", "",
             "| Product | ช่วงนี้ | ช่วงก่อน | เปลี่ยนแปลง | Growth |", "|---|---:|---:|---:|---:|"]
    for signal in row["products"]:
        growth = f"{signal['growthPercent']}%" if signal["growthPercent"] is not None else "N/A (ไม่มีฐาน)"
        lines.append(f"| {_cell(signal['name'])} | {signal['count']} | {signal['previousCount']} | {signal['delta']:+d} | {growth} |")
    if not row["products"]:
        lines += ["", "ไม่มี product signals ในสองช่วงนี้"]
    lines += ["", "## Tag signals", "", "| Tag | ช่วงนี้ | ช่วงก่อน | Delta |", "|---|---:|---:|---:|"]
    lines += [f"| {_cell(s['name'])} | {s['count']} | {s['previousCount']} | {s['delta']:+d} |" for s in row["tags"]]
    lines += ["", "## Tool history", "", "| Tool | Recommendation ล่าสุด | ก่อนหน้า | Observed | Stars delta |", "|---|---|---|---|---:|"]
    for tool in row["tools"]:
        values = [_cell(tool[key]) if tool[key] is not None else "ยังไม่มีข้อมูล"
                  for key in ("name", "recommendation", "previousRecommendation", "observedAt", "starsDelta")]
        lines.append("| " + " | ".join(values) + " |")
    if not row["tools"]:
        lines += ["", "ยังไม่มี tool observations ที่ยืนยันในช่วงนี้"]
    lines += ["", "## Evidence", ""]
    for story in row["stories"]:
        lines.append(f"- {story['coverage']} — {_cell(story['product'])}: {_cell(story['event'])} "
                     f"([primary source]({story['sourceUrl']})); `{story['id']}`")
    if not row["stories"]:
        lines.append("ไม่มีเหตุการณ์ที่บันทึกในช่วงนี้")
    return "\n".join(lines) + "\n"


def rebuild(root, as_of, check=False):
    root = Path(root)
    errors = validate_repository(root)
    if errors:
        raise ValueError("\n".join(errors))
    stories = read_jsonl(root / "data/seen-items.jsonl")
    tools = read_jsonl(root / "data/tools.jsonl")
    observations = read_jsonl(root / "data/tool-observations.jsonl")
    config = read_yaml(root / "config/identity.yml")
    dates = [date.fromisoformat(r["lastReported"]) for r in stories]
    dates += [date.fromisoformat(r["firstSeen"]) for r in tools]
    dates += [date.fromisoformat(r["observedAt"]) for r in observations]
    eligible = [d for d in dates if d <= as_of]
    outputs = {}
    if eligible:
        first = min(eligible)
        weeks, months = set(), set()
        day = first
        while day <= as_of:
            iso = day.isocalendar()
            weeks.add(f"{iso.year:04d}-W{iso.week:02d}")
            months.add(day.strftime("%Y-%m"))
            day += timedelta(days=1)
        for kind, periods in (("weekly", weeks), ("monthly", months)):
            for period in sorted(periods):
                row = build_rollup(stories, tools, observations, kind, period, as_of, config)
                outputs[f"data/rollups/{kind}/{period}.json"] = json.dumps(row, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
                outputs[f"reports/{kind}/{period[:4]}/{period}.md"] = render_rollup(row)
    outputs["data/rollup-state.json"] = json.dumps({"schemaVersion":1, "asOf":as_of.isoformat()}, indent=2) + "\n"
    drift = []
    for relative, content in sorted(outputs.items()):
        path = root / relative
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                drift.append(f"generated file missing or stale: {relative}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    # Stale outputs are reported, never silently deleted.
    for glob in ("data/rollups/**/*.json", "reports/weekly/**/*.md", "reports/monthly/**/*.md"):
        for path in sorted(root.glob(glob)):
            if path.relative_to(root).as_posix() not in outputs:
                drift.append(f"unexpected generated file: {path.relative_to(root).as_posix()}")
    return drift
