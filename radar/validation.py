"""Schema validation plus cross-record invariants; never fetch remote URLs."""
import json
import math
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from jsonschema import Draft202012Validator, FormatChecker


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def _constant(value):
    raise ValueError(f"non-finite JSON value: {value}")


def read_jsonl(path):
    rows = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line, object_pairs_hook=_pairs, parse_constant=_constant)
            if not isinstance(row, dict):
                raise ValueError("expected an object")
            rows.append(row)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{path}:{number}: {exc}") from exc
    return rows


class StrictLoader(yaml.SafeLoader):
    """Safe YAML without silent duplicate-key overwrites."""


def _mapping(loader, node):
    pairs = []
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, str):
            raise ValueError("YAML mapping keys must be strings")
        pairs.append((key, loader.construct_object(value_node, deep=True)))
    return _pairs(pairs)


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def read_yaml(path):
    try:
        data = yaml.load(Path(path).read_text(encoding="utf-8"), Loader=StrictLoader)
        # Forbid dates, sets, cycles and non-finite values that are not JSON data.
        json.dumps(data, allow_nan=False)
        return data
    except (yaml.YAMLError, ValueError, TypeError, RecursionError) as exc:
        raise ValueError(f"{path}: invalid YAML: {exc}") from exc


def _finite(value):
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite(v) for v in value.values())
    if isinstance(value, list):
        return all(_finite(v) for v in value)
    return True


def validate_record(record, kind, root):
    schema_path = Path(root) / "schemas" / f"{kind}.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = [f"/{'/'.join(map(str, e.absolute_path))}: {e.message}"
              for e in validator.iter_errors(record)]
    if not _finite(record):
        errors.append("non-finite number")
    # URI formats alone permit credentials and malformed hostnames.
    if isinstance(record, dict):
        for field in ("sourceUrl", "homepage", "repositoryUrl"):
            value = record.get(field)
            if isinstance(value, str):
                try:
                    parsed = urlsplit(value)
                    if (parsed.scheme not in {"https", "http"} or not parsed.hostname
                            or parsed.username or parsed.password or any(c.isspace() for c in value)):
                        errors.append(f"{field}: expected public HTTP(S) URL without credentials")
                    _ = parsed.port
                except ValueError:
                    errors.append(f"{field}: invalid URL")
    return errors


def validate_repository(root):
    root = Path(root).resolve()
    errors = []
    configs = {}
    for name in ("topics", "radar", "sources", "identity"):
        path = root / "config" / f"{name}.yml"
        try:
            config = read_yaml(path)
            invalid = validate_record(config, name, root)
            errors.extend(f"config/{name}.yml: {e}" for e in invalid)
            if not invalid:
                configs[name] = config
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    if "topics" in configs and sum(configs["topics"]["weights"].values()) != 100:
        errors.append("config/topics.yml: topic weights must sum to 100")
    if "radar" in configs:
        cfg = configs["radar"]
        expected = {"maturity_values": ["Experimental", "Preview", "Production Ready"],
                    "recommendation_values": ["Try", "Watch", "Skip"],
                    "status_values": ["NEW", "UPDATE"]}
        for key, values in expected.items():
            if cfg[key] != values:
                errors.append(f"config/radar.yml: {key} must match schema enums")
    if "identity" in configs:
        from radar.dedupe import normalize
        aliases = {}
        for product, names in configs["identity"]["product_aliases"].items():
            for name in [product, *names]:
                key = normalize(name)
                if key in aliases and aliases[key] != product:
                    errors.append(f"config/identity.yml: ambiguous alias {name}")
                aliases[key] = product

    stores = {}
    for filename, kind in (("seen-items", "story"), ("tools", "tool"),
                           ("tool-observations", "tool-observation")):
        try:
            rows = read_jsonl(root / "data" / f"{filename}.jsonl")
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            rows = []
        valid = []
        ids = set()
        for number, row in enumerate(rows, 1):
            prefix = f"data/{filename}.jsonl:{number}"
            invalid = validate_record(row, kind, root)
            errors.extend(f"{prefix}: {e}" for e in invalid)
            if invalid:
                continue
            if row["id"] in ids:
                errors.append(f"{prefix}: duplicate id {row['id']}")
            ids.add(row["id"])
            valid.append(row)
        stores[filename] = valid

    tools = {row["id"]: row for row in stores["tools"]}
    stories = {}
    identities = set()
    from radar.dedupe import decide, product_key
    identity_config = configs.get("identity", {"product_aliases": {}, "review_threshold": 0.60})
    for row in stores["seen-items"]:
        prefix = f"story {row['id']}"
        if row["firstSeen"] > row["lastReported"]:
            errors.append(f"{prefix}: firstSeen exceeds lastReported")
        report = root / row["reportPath"]
        reported = date.fromisoformat(row["lastReported"])
        expected_path = f"reports/{reported.year}/{reported.isoformat()}.md"
        if row["reportPath"] != expected_path or not report.is_file():
            errors.append(f"{prefix}: reportPath must exist and match lastReported")
        elif row.get("schemaVersion") == 2:
            marker = f"<!-- radar:item {row['id']} -->"
            if marker not in report.read_text(encoding="utf-8"):
                errors.append(f"{prefix}: report missing item marker {marker}")
        for tool_id in row.get("toolIds", []):
            if tool_id not in tools:
                errors.append(f"{prefix}: unknown tool {tool_id}")
        parent = stories.get(row.get("updateOf"))
        if row.get("updateOf"):
            if not parent:
                errors.append(f"{prefix}: updateOf must reference an earlier row")
            elif (parent["lastReported"] > row["lastReported"]
                  or parent.get("productKey", parent["product"]).casefold()
                  != row.get("productKey", row["product"]).casefold()):
                # Aliases bridge legacy product labels to explicit v2 keys.
                if (parent["lastReported"] > row["lastReported"]
                        or product_key(parent, identity_config) != product_key(row, identity_config)):
                    errors.append(f"{prefix}: update parent product/date mismatch")
        if row.get("schemaVersion") == 2:
            label_only = {"product":row["product"]}
            if product_key(label_only, identity_config) != product_key(row, identity_config):
                errors.append(f"{prefix}: productKey must match product label/curated alias")
            decision = decide(row, list(stories.values()), identity_config)
            review = row.get("dedupeReview")
            if review:
                if review["matchedId"] not in stories:
                    errors.append(f"{prefix}: dedupeReview must reference an earlier story")
                if review["reviewedAt"] > row["lastReported"]:
                    errors.append(f"{prefix}: dedupeReview date exceeds lastReported")
            if decision["decision"] == "DUPLICATE":
                errors.append(f"{prefix}: semantic duplicate of {decision['matchedId']}")
            elif decision["decision"] == "REVIEW":
                if (not review or review["matchedId"] != decision["matchedId"]
                        or review["reviewedAt"] > row["lastReported"]):
                    errors.append(f"{prefix}: dedupeReview must resolve {decision['matchedId']} before reporting")
            if row["coverage"] == "UPDATE" and decision["decision"] != "UPDATE":
                errors.append(f"{prefix}: UPDATE requires a distinct, evidenced development")
            if row["publishedAt"] > row["firstSeen"]:
                errors.append(f"{prefix}: publishedAt exceeds firstSeen")
            if row["coverage"] == "UPDATE" and row["sourceType"] == "community":
                errors.append(f"{prefix}: material updates require primary evidence")
            key = (row["productKey"], row["eventKey"], row.get("version", "").casefold(), row["milestone"].casefold())
            if key in identities:
                errors.append(f"{prefix}: duplicate structured event identity")
            identities.add(key)
        stories[row["id"]] = row

    latest = {}
    for row in stores["tool-observations"]:
        tool = tools.get(row["toolId"])
        if not tool:
            errors.append(f"observation {row['id']}: unknown tool {row['toolId']}")
        elif row["observedAt"] < tool["firstSeen"]:
            errors.append(f"observation {row['id']}: observation predates tool")
        if row["observedAt"] <= latest.get(row["toolId"], ""):
            errors.append(f"observation {row['id']}: one observation per tool/day, ordered by date")
        latest[row["toolId"]] = row["observedAt"]
        for story_id in row["storyIds"]:
            if story_id not in stories:
                errors.append(f"observation {row['id']}: unknown story {story_id}")
            elif stories[story_id]["lastReported"] > row["observedAt"]:
                errors.append(f"observation {row['id']}: referenced story is in the future")
    return errors
