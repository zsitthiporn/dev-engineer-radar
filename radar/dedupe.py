"""Conservative semantic identity matching. Fuzzy evidence only requests review."""
import re
import unicodedata
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def normalize(value):
    text = unicodedata.normalize("NFKC", value).casefold().strip()
    text = text.replace("c#", "csharp").replace(".net", "dotnet")
    return " ".join(re.findall(r"[^\W_]+", text, re.UNICODE))


def canonical_url(value):
    parts = urlsplit(value)
    host = (parts.hostname or "").lower()
    if ":" in host:
        host = f"[{host}]"
    port = parts.port
    if port and (parts.scheme.lower(), port) not in {("https", 443), ("http", 80)}:
        host += f":{port}"
    query = [(key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
             if not key.casefold().startswith("utm_")
             and key.casefold() not in {"fbclid", "gclid", "mc_cid", "mc_eid"}]
    return urlunsplit((parts.scheme.lower(), host, parts.path.rstrip("/") or "/", urlencode(query), ""))


def product_key(row, config):
    label = normalize(row.get("productKey", row["product"]))
    for key, aliases in config["product_aliases"].items():
        if label in {normalize(key), *(normalize(alias) for alias in aliases)}:
            return key
    return label.replace(" ", "-")


def _event(row):
    return normalize(row.get("eventKey", row["event"]))


def _milestone(row):
    version = unicodedata.normalize("NFKC", row.get("version", "")).casefold().strip()
    return version, normalize(row.get("milestone", row["status"]))


def _similarity(left, right):
    a, b = normalize(left), normalize(right)
    tokens_a, tokens_b = set(a.split()), set(b.split())
    overlap = len(tokens_a & tokens_b) / max(1, len(tokens_a | tokens_b))
    return max(overlap, SequenceMatcher(None, a, b, autojunk=False).ratio())


def _result(decision, reason, row=None, similarity=None):
    result = {"decision": decision, "reason": reason, "matchedId": row["id"] if row else None}
    if similarity is not None:
        result["similarity"] = round(similarity, 4)
    return result


def _material(candidate, parent):
    if (normalize(candidate["event"]) == normalize(parent["event"])
            and _milestone(candidate) == _milestone(parent)):
        return False
    if candidate.get("materialChange") in {"milestone", "release"} and _milestone(candidate) == _milestone(parent):
        return False
    return (candidate.get("coverage") == "UPDATE" and candidate.get("updateOf") == parent["id"]
            and candidate.get("materialChange") and candidate.get("changeSummary", "").strip()
            and candidate.get("evidenceSummary", "").strip()
            and candidate.get("sourceType") in {"official", "repository", "documentation"}
            and (_event(candidate) != _event(parent) or _milestone(candidate) != _milestone(parent)))


def decide(candidate, history, config):
    """Return NEW, DUPLICATE, UPDATE or REVIEW with a matched ID and reason.

    Callers validate candidates first. Scores are text similarity, not confidence
    probabilities. Do not publish REVIEW candidates until manually resolved.
    """
    rows = sorted(history, key=lambda row: (row.get("lastReported", ""), row["id"]), reverse=True)
    product = product_key(candidate, config)
    same_product = [row for row in rows if product_key(row, config) == product]
    collisions = [row for row in rows if row["id"] == candidate["id"]]
    if collisions:
        old = collisions[0]
        if (product_key(old, config), _event(old), _milestone(old)) == (product, _event(candidate), _milestone(candidate)):
            return _result("DUPLICATE", "immutable story ID already recorded", old)
        return _result("REVIEW", "ID collision: changed events need a new ID", old)
    for row in same_product:
        if _event(row) == _event(candidate) and _milestone(row) == _milestone(candidate):
            return _result("DUPLICATE", "same product, event and version/milestone", row)
    parent = next((row for row in rows if row["id"] == candidate.get("updateOf")), None)
    if candidate.get("updateOf") or candidate.get("coverage") == "UPDATE":
        if not parent or product_key(parent, config) != product:
            return _result("REVIEW", "update parent missing or belongs to another product", parent)
        if _material(candidate, parent):
            return _result("UPDATE", "new structured development with declared primary evidence", parent)
        return _result("REVIEW", "update lacks distinct development or primary evidence", parent)
    for row in same_product:
        if _event(row) == _event(candidate):
            return _result("REVIEW", "same event with changed version/milestone; verify material update", row)
    source = canonical_url(candidate["sourceUrl"])
    for row in rows:
        if canonical_url(row["sourceUrl"]) == source:
            return _result("REVIEW", "same source can describe multiple capabilities/products", row)
    matches = [(_similarity(candidate["event"], row["event"]), row) for row in same_product]
    matches.sort(key=lambda pair: (pair[0], pair[1]["id"]), reverse=True)
    if matches and matches[0][0] >= config["review_threshold"]:
        similarity, row = matches[0]
        return _result("REVIEW", "similar event wording; check semantic identity manually", row, similarity)
    return _result("NEW", "no prior identity or review signal found")
