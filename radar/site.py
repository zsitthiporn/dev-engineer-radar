"""Build an allowlisted reading experience. Never copy the repository checkout."""
import argparse
import hashlib
import html
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from radar.validation import read_jsonl, read_yaml, validate_record, validate_repository

TOPICS = {
    "ai_developer_tools": ("AI & Developer Tools", "Coding agents, MCP และเครื่องมือที่ช่วยทำงานจริง", "AI"),
    "devops_cloud_native": ("DevOps & Cloud Native", "Kubernetes, Docker และระบบที่ใช้งานได้จริง", "OPS"),
    "dotnet_backend": (".NET & Backend", "C#, ASP.NET Core, data access และ performance", ".NET"),
    "git_cicd_observability": ("Git, CI/CD & Observability", "การส่งมอบซอฟต์แวร์และมองเห็นพฤติกรรมระบบ", "CI"),
    "infrastructure_architecture_security": ("Architecture & Security", "Infrastructure, distributed systems และขอบเขตความปลอดภัย", "SYS"),
}
DEFAULT_URL = "https://zsitthiporn.github.io/dev-engineer-radar/"
ASSETS = ("style.css", "app.js", "mark.svg")


def public_url(value):
    """Public HTTPS links only; credentials/token queries never enter the export."""
    try:
        p = urlsplit(value)
        if (p.scheme != "https" or not p.hostname or p.username or p.password or p.query
                or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)
                or p.port not in (None, 443)):
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError("expected public HTTPS URL without credentials/query parameters") from None
    return value


def publications(root):
    errors = validate_repository(root)
    if errors:
        raise ValueError("\n".join(errors))
    history = {r["id"]: r for r in read_jsonl(root / "data/seen-items.jsonl")}
    rows = read_jsonl(root / "data/publications.jsonl")
    ids = set()
    for row in rows:
        invalid = validate_record(row, "publication", root)
        if invalid:
            raise ValueError("publication: " + "; ".join(invalid))
        if row["id"] in ids or row["id"] not in history:
            raise ValueError("publication requires a unique recorded story ID")
        ids.add(row["id"])
        if not row["publishedAt"] <= row["editionDate"] <= row["reviewedAt"] or row["reviewedAt"] < history[row["id"]]["lastReported"]:
            raise ValueError("publication review must follow source publication and recorded coverage")
        urls = [public_url(ref["url"]) for ref in row["references"]]
        if history[row["id"]]["sourceUrl"] not in urls:
            raise ValueError("publication must retain the recorded primary source")
    return sorted(rows, key=lambda r: (r["reviewedAt"], r["publishedAt"], r["id"]), reverse=True)


def esc(value):
    return html.escape(str(value), quote=True)


def stamp(value):
    d = date.fromisoformat(value)
    return f"{d.day:02d}.{d.month:02d}.{d.year}"


def chips(tags):
    return "".join(f'<span class="chip">{esc(tag)}</span>' for tag in tags)


def card(row, prefix="", lead=False):
    label, _, glyph = TOPICS[row["topic"]]
    corpus = " ".join([row["title"], row["summary"], *row["tags"], *[s["text"] for s in row["sections"]]])
    return f'''<article class="story-card {'lead-card' if lead else ''}" data-topic="{row['topic']}" data-recommendation="{row['recommendation']}" data-search="{esc(corpus.casefold())}">
<div class="card-top"><span class="topic-label">{esc(label)}</span><span class="verdict {row['recommendation'].lower()}">{row['recommendation']}</span></div>
<span class="story-symbol" aria-hidden="true">{esc(glyph)}</span>
<h3><a href="{prefix}articles/{row['id']}/">{esc(row['title'])}<span class="stretched-link" aria-hidden="true"></span></a></h3>
<p>{esc(row['summary'])}</p><div class="tags">{chips(row['tags'][:3])}</div>
<div class="card-foot"><span>{stamp(row['publishedAt'])} · {esc(row['references'][0]['publisher'])}</span><span aria-hidden="true">↗</span></div></article>'''


def frame(title, body, base, relative, site_url, active="news", description=None):
    nav = [("news", "ข่าวล่าสุด", ""), ("coverage", "เราติดตามอะไร", "coverage/"), ("archive", "สรุปย้อนหลัง", "archive/")]
    links = "".join(f'<a href="{base}{path or "./"}" {"aria-current=\"page\"" if key == active else ""}>{label}</a>' for key, label, path in nav)
    description = description or "คัดข่าววิศวกรรมซอฟต์แวร์ อธิบายผลกระทบ และเชื่อมต่อไปยังแหล่งข้อมูลต้นทาง"
    return f'''<!doctype html><html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · Dev Engineer Radar</title><meta name="description" content="{esc(description)}"><meta name="theme-color" content="#f5f6f3">
<link rel="canonical" href="{esc(site_url + relative)}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:type" content="website">
<link rel="icon" href="{base}assets/mark.svg" type="image/svg+xml"><link rel="stylesheet" href="{base}assets/style.css"><script src="{base}assets/app.js" defer></script>
<link rel="alternate" type="application/rss+xml" title="Dev Engineer Radar" href="{base}feed.xml"></head><body>
<a class="skip" href="#main">ข้ามไปเนื้อหา</a><header class="site-header"><div class="header-inner"><a class="brand" href="{base}./"><img src="{base}assets/mark.svg" width="34" height="34" alt=""><span>dev engineer<span class="brand-sub">RADAR / ENGINEERING INTELLIGENCE</span></span></a><nav aria-label="เมนูหลัก">{links}</nav><a class="feed-link" href="{base}feed.xml">RSS ↗</a></div></header>
<main id="main">{body}</main><footer class="site-footer"><div><a class="footer-brand" href="{base}./">dev engineer radar<span aria-hidden="true"> ●</span></a><p>อ่านให้เข้าใจ เลือกใช้ให้เหมาะกับงาน</p></div><div class="footer-right"><a href="{base}coverage/">ขอบเขตการติดตาม</a><a href="{base}feed.xml">RSS feed ↗</a><p>Primary sources · Thai insights · No tracking</p></div></footer></body></html>'''


def homepage(rows):
    as_of = max((r["reviewedAt"] for r in rows), default="")
    latest = f"ตรวจแหล่งข้อมูลล่าสุด {stamp(as_of)}" if as_of else "ยังไม่มีข่าวเผยแพร่"
    filters = '<button type="button" data-filter="all" aria-pressed="true">ทั้งหมด</button>' + "".join(
        f'<button type="button" data-filter="{key}" aria-pressed="false">{esc(label)}</button>' for key, (label, _, _) in TOPICS.items())
    cards = "".join(card(row, lead=i == 0) for i, row in enumerate(rows))
    return f'''<section class="hero"><div class="hero-copy"><p class="eyebrow"><span class="live-dot"></span> THE ENGINEERING SIGNAL</p><h1>ข่าวที่ควรรู้.<br><span>ความรู้ที่ใช้ได้จริง.</span></h1><p class="hero-description">คัดสัญญาณที่มีความหมายสำหรับคนสร้างซอฟต์แวร์<br>จาก AI และ .NET ไปถึง Kubernetes และโครงสร้างพื้นฐาน</p><div class="hero-actions"><a class="button primary" href="#latest">อ่านข่าวล่าสุด <span aria-hidden="true">↓</span></a><a class="text-link" href="coverage/">ดูสิ่งที่เราติดตาม ↗</a></div><p class="edition">{latest} <span>·</span> ASIA / BANGKOK</p></div><div class="radar-panel" aria-label="5 กลุ่มหัวข้อที่ติดตาม"><div class="radar-orbit"><div class="orbit o1"></div><div class="orbit o2"></div><div class="orbit o3"></div><div class="radar-axis"></div><div class="radar-axis vertical"></div><div class="radar-sweep"></div><div class="radar-core">R<span>high signal</span></div><span class="orbit-point p1">.NET</span><span class="orbit-point p2">AI</span><span class="orbit-point p3">CLOUD</span></div><div class="radar-caption"><span>01 — 05 / FOCUS AREAS</span><span>ค้นหา · เชื่อมโยง · เข้าใจ</span></div></div></section>
<div class="principles"><span>อ้างอิงแหล่งต้นทาง <b>↗</b></span><span>อธิบายผลกระทบ <b>↗</b></span><span>มีสิ่งที่ลองทำต่อ <b>↗</b></span><span>เก็บความรู้ต่อเนื่อง <b>↗</b></span></div>
<section id="latest" class="latest"><div class="section-heading"><div><p class="eyebrow">THE READING DESK</p><h2>สัญญาณล่าสุด<span class="count">{len(rows)}</span></h2></div><a class="text-link" href="archive/">สรุปรายสัปดาห์ / เดือน ↗</a></div>
<div class="search-toolbar"><label class="search-box"><span aria-hidden="true">⌕</span><span class="sr-only">ค้นหาข่าว</span><input id="search" type="search" placeholder="ค้นหาเครื่องมือ หัวข้อ หรือสิ่งที่อยากรู้…" autocomplete="off"><kbd>/</kbd></label><label class="verdict-select"><span class="sr-only">กรองคำแนะนำ</span><select id="verdict"><option value="all">ทุกคำแนะนำ</option><option>Try</option><option>Watch</option><option>Skip</option></select></label></div>
<div class="filters" role="group" aria-label="กรองหัวข้อ">{filters}</div><p id="result-count" class="result-count" aria-live="polite">{len(rows)} บทความ · คัดจาก primary sources</p><div class="story-grid">{cards}</div><div id="empty" class="empty" hidden><h3>ยังไม่พบข่าวที่ตรงกับคำค้น</h3><p>ลองชื่อเครื่องมือหรือคำที่กว้างขึ้น</p><button id="reset" type="button" class="button">ล้างตัวกรอง</button></div></section>
<section class="coverage-callout"><div><p class="eyebrow">YOUR ENGINEERING COMPASS</p><h2>รู้ว่าเรามองหาอะไร<br>แล้วทำไมจึงเลือกข่าวนี้</h2><p>ดูหัวข้อ น้ำหนักความสำคัญ และเกณฑ์ที่ใช้คัดข่าว<br>เพื่อให้ทุกเรื่องบน Radar มีที่มาที่เข้าใจได้</p></div><a class="button primary" href="coverage/">สำรวจขอบเขต Radar ↗</a></section>'''


def article(row, rows):
    sections = "".join(f'<section id="section-{i}"><p class="section-kind">{ {"fact":"จากแหล่งต้นทาง", "analysis":"มุมมองของ Radar", "action":"ลองทำต่อ"}[s["kind"]] }</p><h2>{esc(s["heading"])}</h2><p>{esc(s["text"])}</p></section>' for i, s in enumerate(row["sections"]))
    toc = "".join(f'<a href="#section-{i}">{esc(s["heading"])}</a>' for i, s in enumerate(row["sections"]))
    refs = "".join(f'<li><span class="ref-number">{i+1:02d}</span><div><a href="{esc(r["url"])}" rel="noopener noreferrer">{esc(r["title"])} ↗</a><p>{esc(r["publisher"])}</p></div></li>' for i, r in enumerate(row["references"]))
    related = "".join(card(r, "../../") for r in rows if r["id"] != row["id"] and (r["topic"] == row["topic"] or set(r["tags"]) & set(row["tags"])))
    return f'''<div class="article-heading"><a class="breadcrumb" href="../../">← ข่าวทั้งหมด</a><p class="eyebrow">{esc(TOPICS[row['topic']][0])} / FIELD NOTES</p><h1>{esc(row['title'])}</h1><p class="article-deck">{esc(row['summary'])}</p><div class="article-meta"><span>{stamp(row['publishedAt'])} · {esc(row['references'][0]['publisher'])}</span><span>ตรวจ primary source {stamp(row['reviewedAt'])}</span></div><div class="tags">{chips(row['tags'])}</div></div><div class="article-layout"><article class="article-body">{sections}<section id="references" class="references"><p class="eyebrow">READ THE ORIGINAL</p><h2>References & อ่านต่อ</h2><ol>{refs}</ol><p class="note">ส่วน “มุมมองของ Radar” และ “ลองทำต่อ” เป็นการวิเคราะห์และข้อเสนอของเรา ผลการทดสอบจริงขึ้นกับสภาพแวดล้อมของคุณ</p></section></article><aside class="reading-aside"><div class="decision-card"><p class="eyebrow">RADAR VERDICT</p><span class="verdict {row['recommendation'].lower()}">{row['recommendation']}</span><h3>{esc(row['maturity'])}</h3><dl><dt>เวลาทดลองโดยประมาณ</dt><dd>{esc(row['effort'])}</dd><dt>เหมาะกับ</dt><dd>{esc(' / '.join(row['tags'][:3]))}</dd></dl><p>คำแนะนำจาก Radar<br>ไม่ใช่คำรับรองจากผู้ผลิต</p></div><nav class="toc" aria-label="ในบทความนี้"><p class="eyebrow">ในบทความนี้</p>{toc}<a href="#references">References & อ่านต่อ</a></nav></aside></div>{'<section class="related"><p class="eyebrow">CONNECTED SIGNALS</p><h2>อ่านเรื่องที่เชื่อมกัน</h2><div class="story-grid">' + related + '</div></section>' if related else ''}'''


def coverage(config):
    panels = "".join(f'<article class="focus-card"><span class="focus-number">0{i+1}</span><div><h2>{esc(TOPICS[key][0])}</h2><p>{esc(TOPICS[key][1])}</p><div class="weight-bar"><span style="width:{weight}%"></span></div></div><strong>{weight}<small>%</small></strong></article>' for i, (key, weight) in enumerate(config["weights"].items()))
    def group(key, title, note):
        return f'<section class="coverage-group"><h2>{title}</h2><p>{note}</p><div class="tags">{chips(config[key])}</div></section>'
    return f'''<section class="page-heading"><p class="eyebrow">THE RADAR SCOPE</p><h1>เราติดตามอะไร.<br><span>และอะไรสำคัญกับเรา.</span></h1><p>Radar ให้ความสำคัญกับสิ่งที่เปลี่ยนวิธีสร้าง ส่งมอบ และดูแลซอฟต์แวร์<br>น้ำหนักด้านล่างสะท้อนความสนใจในการคัดข่าว ไม่ใช่คะแนนความนิยมของตลาด</p></section><section class="focus-list">{panels}</section>{group('high_priority','ติดตามเป็นพิเศษ','เทคโนโลยีหลักที่ต้องการเห็นข่าวและผลกระทบอย่างสม่ำเสมอ')}{group('medium_priority','ติดตามเมื่อมีสัญญาณสำคัญ','เลือกเมื่อมีความเปลี่ยนแปลงที่เกี่ยวข้องกับการใช้งานจริง')}{group('active_discovery','เปิดรับเครื่องมือใหม่','มองหาเครื่องมือที่แก้ปัญหาได้ชัด และทดลองได้ด้วยตัวเอง')}<section class="selection-panel"><p class="eyebrow">EDITORIAL PRINCIPLES</p><h2>เราเลือกเรื่องอย่างไร</h2><div class="selection-grid"><div><h3>แหล่งข้อมูลต้องตรวจได้</h3><p>เริ่มจาก release notes, เอกสาร หรือบทความของผู้พัฒนา พร้อมแยกข้อเท็จจริงออกจากมุมมองของ Radar</p></div><div><h3>ต้องมีผลต่อการทำงาน</h3><p>อธิบายว่าเรื่องนี้เปลี่ยนอะไร เหมาะกับใคร และมีสิ่งที่ควรลองหรือเฝ้าดูอย่างไร</p></div><div><h3>ลดข่าวซ้ำ เก็บพัฒนาการ</h3><p>นับเหตุการณ์และ milestone ที่เปลี่ยนจริง ข่าวที่คล้ายกันต้องผ่านการตรวจ ไม่ลบทิ้งด้วยคะแนนความคล้ายอย่างเดียว</p></div></div><details><summary>ประเภทข่าวที่ให้น้ำหนักน้อย</summary><ul>{''.join('<li>' + esc(s) + '</li>' for s in config['low_value_patterns'])}</ul></details></section>'''


def archive(rows):
    groups = {}
    for row in rows:
        day = date.fromisoformat(row["editionDate"])
        iso = day.isocalendar()
        for kind, period in (("weekly", f"{iso.year}-W{iso.week:02d}"), ("monthly", day.strftime("%Y-%m"))):
            groups.setdefault((kind, period), []).append(row)
    panels = []
    for (kind, period), entries in sorted(groups.items(), reverse=True):
        counts = Counter(TOPICS[r["topic"]][0] for r in entries)
        signals = "".join(f'<li><span>{esc(key)}</span><strong>{value}</strong></li>' for key, value in counts.most_common())
        links = "".join(f'<li><a href="../articles/{r["id"]}/">{esc(r["title"])} ↗</a></li>' for r in entries)
        panels.append(f'<section class="rollup-card"><p class="eyebrow">{"WEEKLY" if kind == "weekly" else "MONTHLY"} DIGEST</p><h2>{period}</h2><p>{len(entries)} ข่าวเผยแพร่ · snapshot {stamp(max(r["reviewedAt"] for r in entries))}</p><ul class="signal-list">{signals}</ul><details><summary>อ่านข่าวในช่วงนี้</summary><ul class="archive-links">{links}</ul></details></section>')
    return '<section class="page-heading"><p class="eyebrow">THE KNOWLEDGE ARCHIVE</p><h1>มองย้อนกลับ.<br><span>เห็นภาพที่ต่อเนื่อง.</span></h1><p>สรุปจากข่าวที่ผ่านการคัดและเผยแพร่บนเว็บเท่านั้น<br>จำนวนข่าวสะท้อน coverage ของ Radar ไม่ใช่ adoption ของอุตสาหกรรม</p></section><div class="archive-grid">' + ''.join(panels) + '</div><p class="archive-note">ช่วงปัจจุบันอาจยังไม่ครบสัปดาห์หรือเดือน วันที่ไม่มีข่าวไม่ได้แปลว่าไม่มีเหตุการณ์ใหม่ในตลาด</p>'


def build(root, out, site_url=DEFAULT_URL):
    root, out = Path(root).resolve(), Path(out).resolve()
    public_url(site_url)
    site_url = site_url.rstrip("/") + "/"
    # Fail closed: never overwrite the checkout or silently retain stale export files.
    if out == root or out in root.parents or (out.exists() and any(out.iterdir())):
        raise ValueError("output must be an empty directory outside repository inputs")
    rows = publications(root)
    config = read_yaml(root / "config/topics.yml")
    outputs = {"index.html": frame("ข่าวที่ควรรู้ ความรู้ที่ใช้ได้จริง", homepage(rows), "", "", site_url),
               "coverage/index.html": frame("เราติดตามอะไร", coverage(config), "../", "coverage/", site_url, "coverage"),
               "archive/index.html": frame("สรุปย้อนหลัง", archive(rows), "../", "archive/", site_url, "archive"),
               "404.html": frame("ไม่พบหน้านี้", '<section class="page-heading"><p class="eyebrow">404 / OUTSIDE THE RADAR</p><h1>ไม่พบหน้านี้</h1><p>กลับมาเลือกเรื่องที่อยากอ่านจากข่าวล่าสุด</p><a class="button primary" href="' + esc(site_url) + '">กลับหน้าข่าว</a></section>', site_url, "404.html", site_url),
               ".nojekyll": "", "robots.txt": f"User-agent: *\nAllow: /\nSitemap: {site_url}sitemap.xml\n"}
    public_rows = []
    for row in rows:
        relative = f"articles/{row['id']}/"
        outputs[relative + "index.html"] = frame(row["title"], article(row, rows), "../../", relative, site_url, description=row["summary"])
        # Schema disallows hidden fields. Project explicitly even if schemas evolve later.
        public_rows.append({key: row[key] for key in ("id", "title", "summary", "topic", "tags", "publishedAt", "editionDate", "reviewedAt", "recommendation", "maturity", "effort", "sections", "references")} | {"url": site_url + relative})
    outputs["feed.json"] = json.dumps({"schemaVersion": 1, "siteUrl": site_url, "items": public_rows}, ensure_ascii=False, indent=2) + "\n"
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    for key, value in (("title", "Dev Engineer Radar"), ("link", site_url), ("description", "Engineering signals with primary references"), ("language", "th")):
        ET.SubElement(channel, key).text = value
    for row in public_rows:
        item = ET.SubElement(channel, "item")
        for key, value in (("title", row["title"]), ("link", row["url"]), ("guid", row["url"]), ("description", row["summary"])):
            ET.SubElement(item, key).text = value
    outputs["feed.xml"] = ET.tostring(rss, encoding="unicode", xml_declaration=True)
    sitemap = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for path in sorted(p for p in outputs if p.endswith("index.html")):
        ET.SubElement(ET.SubElement(sitemap, "url"), "loc").text = site_url + path.removesuffix("index.html")
    outputs["sitemap.xml"] = ET.tostring(sitemap, encoding="unicode", xml_declaration=True)
    for asset in ASSETS:
        path = root / "web" / asset
        if path.is_symlink():
            raise ValueError("symlink assets are forbidden")
        outputs["assets/" + asset] = path.read_text(encoding="utf-8")
    out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for relative, content in sorted(outputs.items()):
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        blob = content.encode("utf-8")
        target.write_bytes(blob)
        manifest[relative] = {"sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob)}
    (out / "manifest.json").write_text(json.dumps({"schemaVersion": 1, "files": manifest}, indent=2) + "\n", encoding="utf-8", newline="\n")
    return len(rows), len(manifest) + 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("dist"))
    parser.add_argument("--site-url", default=DEFAULT_URL)
    args = parser.parse_args(argv)
    try:
        articles, files = build(args.root, args.output, args.site_url)
        print(f"Public site built: {articles} articles, {files} allowlisted files")
        return 0
    except (ValueError, OSError) as exc:
        print(f"Site build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
