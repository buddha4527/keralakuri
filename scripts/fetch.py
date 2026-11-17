#!/usr/bin/env python3
"""Fetch new Kerala lottery results from the official website, check them, save them.

    python scripts/fetch.py            # look for new results (normal daily run)
    python scripts/fetch.py --max 30   # backfill: up to 30 recent draws
    python scripts/fetch.py --inbox    # only process results pasted into data/inbox/

Exit code 0 = fine (new result saved, or nothing new yet).
Exit code 2 = something needs a human look (details in data/status.json and data/review/).
Nothing that fails a check is ever published.
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import time
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from kk.lotteries import WEEKLY, display_name, slugify  # noqa: E402
from kk.parse import (ValidationError, html_to_text, parse_list_page,  # noqa: E402
                      parse_result_text, validate)

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text())
DRAWS = ROOT / "data" / "draws"
REVIEW = ROOT / "data" / "review"
INBOX = ROOT / "data" / "inbox"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
UA = "Mozilla/5.0 (compatible; KeralaKuriBot/1.0; +" + CONFIG["site_url"] + ")"


def get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # network hiccups are common at 3-4 PM
            last = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"could not download {url}: {last}")


def record_path(row):
    return DRAWS / f"{row['date']}-{row['code']}-{row['draw_no']}.json"


def build_record(row, tiers):
    name = display_name(row["code"], row["raw_name"])
    y, m, d = row["date"].split("-")
    weekday = dt.date(int(y), int(m), int(d)).weekday()
    expected = WEEKLY.get(row["code"], {}).get("weekday")
    if expected is not None and expected != weekday:
        raise ValidationError(f"{row['code']} is normally drawn on another weekday")
    return {
        "code": row["code"],
        "draw_no": row["draw_no"],
        "name": name,
        "raw_name": row["raw_name"],
        "date": row["date"],
        "slug": f"{slugify(name)}-{row['code'].lower()}-{row['draw_no']}-{d}-{m}-{y}",
        "source_url": row.get("source_url"),
        "fetched_at": dt.datetime.now(IST).isoformat(timespec="seconds"),
        "checks": "passed",
        "tiers": tiers,
    }


def save_or_review(row, text, problems):
    try:
        tiers = parse_result_text(text)
        validate(tiers)
        rec = build_record(row, tiers)
        # The result page header normally names the draw; if it names a different one, stop.
        hdr = re.search(r"\b([A-Z]{2})\s*-\s*(\d{1,4})\b", text[:600])
        if hdr and hdr.group(1) == row["code"] and int(hdr.group(2)) != row["draw_no"]:
            raise ValidationError(f"page header says {hdr.group(0)}, list says {row['code']}-{row['draw_no']}")
        record_path(row).write_text(json.dumps(rec, ensure_ascii=False, indent=1))
        print(f"saved {rec['slug']}")
        return True
    except ValidationError as e:
        REVIEW.mkdir(parents=True, exist_ok=True)
        (REVIEW / f"{row['date']}-{row['code']}-{row['draw_no']}.txt").write_text(
            f"PROBLEM: {e}\nSOURCE: {row.get('source_url')}\n\n{text}")
        problems.append(f"{row['code']}-{row['draw_no']} ({row['date']}): {e}")
        print(f"NOT published {row['code']}-{row['draw_no']}: {e}")
        return False


def run_official(max_new, problems):
    rows = parse_list_page(get(CONFIG["official_list_url"]))
    if not rows:
        problems.append("official results list could not be read (page layout may have changed)")
        return 0
    saved = 0
    for row in rows[:max_new]:
        if record_path(row).exists():
            continue
        text = html_to_text(get(row["source_url"]))
        saved += save_or_review(row, text, problems)
    return saved


INBOX_HEAD = re.compile(r"^\s*(?:(.+?)\s+)?([A-Z]{2})\s*-\s*(\d+)\s+(\d{2})[/.-](\d{2})[/.-](\d{4})\s*$")


def run_inbox(problems):
    """Manual fallback: paste the official result text into data/inbox/anything.txt.
    First line: CODE-NO DD/MM/YYYY   e.g.  BT-80 16/11/2026
    Everything below: the result text copied from the official page."""
    saved = 0
    for f in sorted(INBOX.glob("*.txt")):
        first, _, body = f.read_text().partition("\n")
        m = INBOX_HEAD.match(first.upper())
        if not m:
            problems.append(f"{f.name}: first line must look like 'BT-80 16/11/2026'")
            continue
        raw, code, no, dd, mm, yyyy = m.groups()
        row = {"raw_name": raw or WEEKLY.get(code, {}).get("name", code), "code": code,
               "draw_no": int(no), "date": f"{yyyy}-{mm}-{dd}", "source_url": None}
        if save_or_review(row, body, problems):
            f.unlink()
            saved += 1
    return saved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=3, help="how many newest listed draws to look at")
    ap.add_argument("--inbox", action="store_true", help="only process data/inbox/")
    a = ap.parse_args()
    DRAWS.mkdir(parents=True, exist_ok=True)
    problems = []
    saved = run_inbox(problems)
    if not a.inbox:
        try:
            saved += run_official(a.max, problems)
        except RuntimeError as e:
            problems.append(str(e))
    status = {"checked_at": dt.datetime.now(IST).isoformat(timespec="seconds"),
              "new_results": saved, "problems": problems}
    (ROOT / "data" / "status.json").write_text(json.dumps(status, indent=1))
    print(json.dumps(status, indent=1))
    return 2 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
