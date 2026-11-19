#!/usr/bin/env python3
"""Load past results from a kk-history.json file gathered from theweek.in.

    python scripts/import_theweek.py path/to/kk-history.json

Every draw goes through the same checks as official results, plus:
numbers inside each prize list must be in ascending order (as published).
Draws that fail are skipped and listed; nothing is guessed or repaired.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from fetch import DRAWS, build_record  # noqa: E402
from kk.parse import ValidationError, validate  # noqa: E402
from kk.theweek import parse_article  # noqa: E402


def main(path):
    items = json.loads(pathlib.Path(path).read_text())
    ok, skipped, existing = 0, [], 0
    for it in items:
        label = it.get("title", it["url"])[:70]
        try:
            row, tiers = parse_article(it["text"])
            validate(tiers)
            for t in tiers:
                if t["endings"] and t["endings"] != sorted(t["endings"]):
                    raise ValidationError(f"prize {t['tier']} numbers not in order")
            row["source_url"] = it["url"]
            out = DRAWS / f"{row['date']}-{row['code']}-{row['draw_no']}.json"
            if out.exists():
                existing += 1
                continue
            rec = build_record(row, tiers)
            rec["source"] = "theweek.in (copy of the official result)"
            out.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
            ok += 1
        except (ValueError, ValidationError) as e:
            skipped.append(f"{label}: {e}")
    print(f"imported {ok}, already had {existing}, skipped {len(skipped)}")
    for s in skipped:
        print("  SKIPPED", s)


if __name__ == "__main__":
    main(sys.argv[1])
