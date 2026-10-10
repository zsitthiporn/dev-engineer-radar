"""Offline command-line interface for repo producers and reviewers."""
import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from radar.dedupe import decide
from radar.rollups import rebuild
from radar.validation import _pairs, _constant, read_jsonl, read_yaml, validate_record, validate_repository


def check_append_only(root, base):
    if not re.fullmatch(r"[0-9a-fA-F]{40}", base):
        raise ValueError("--base requires a full 40-character commit SHA")
    subprocess.run(["git", "cat-file", "-e", f"{base}^{{commit}}"], cwd=root, check=True, capture_output=True)
    errors = []
    for path in ("data/seen-items.jsonl", "data/tool-observations.jsonl"):
        listing = subprocess.run(["git", "ls-tree", "--name-only", base, "--", path], cwd=root,
                                 check=True, capture_output=True, text=True)
        if not listing.stdout.strip():
            continue
        old = subprocess.run(["git", "show", f"{base}:{path}"], cwd=root,
                             check=True, capture_output=True).stdout.decode("utf-8")
        old_rows = [json.loads(line, object_pairs_hook=_pairs, parse_constant=_constant) for line in old.splitlines()]
        current = read_jsonl(Path(root) / path)
        if current[:len(old_rows)] != old_rows:
            errors.append(f"{path}: history must be append-only relative to {base}")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate schemas and history references")
    validate.add_argument("--base", help="enforce append-only logs against a full commit SHA")
    dedupe = commands.add_parser("dedupe", help="classify one schema-valid candidate; never writes data")
    dedupe.add_argument("candidate", type=Path)
    rollup = commands.add_parser("rollup", help="rebuild derived weekly/monthly views")
    rollup.add_argument("--as-of", type=date.fromisoformat)
    rollup.add_argument("--check", action="store_true", help="fail on drift without writing files")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            errors = validate_repository(args.root)
            if args.base:
                errors.extend(check_append_only(args.root, args.base))
        elif args.command == "dedupe":
            errors = validate_repository(args.root)
            candidate = json.loads(args.candidate.read_text(encoding="utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
            errors.extend(validate_record(candidate, "story", args.root))
            if not isinstance(candidate, dict) or candidate.get("schemaVersion") != 2:
                errors.append("dedupe candidates require schemaVersion 2")
            if not errors:
                result = decide(candidate, read_jsonl(args.root / "data/seen-items.jsonl"),
                                read_yaml(args.root / "config/identity.yml"))
                print(json.dumps(result, ensure_ascii=False))
                return 0
        else:
            as_of = args.as_of
            if as_of is None:
                state = json.loads((args.root / "data/rollup-state.json").read_text(encoding="utf-8"), object_pairs_hook=_pairs)
                if state.get("schemaVersion") != 1:
                    raise ValueError("unsupported rollup-state schemaVersion")
                as_of = date.fromisoformat(state["asOf"])
            errors = rebuild(args.root, as_of, check=args.check)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        print("Validation passed" if args.command == "validate" else "Rollup check passed" if args.check else "Rollups generated")
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
