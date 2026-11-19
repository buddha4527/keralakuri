"""Reader for result articles on theweek.in (used to load past results).

Article text looks like:
  The result for the weekly Bhagyathara BT-80 draw conducted on Monday, November 16, 2026, has been declared.
  The first prize of ₹1 Crore goes to the lottery ticket number-
  BV 543398 (ERNAKULAM)
  Agent Name: ...
  2nd prize (₹30,00,000):
  BV 362422 (THRISSUR)
  Consolation prize (₹5000):
  BN 543398 ...
  4th prize (₹5000):
  1504  2832 ...
"""
import datetime as dt
import re

from .parse import ENDING, TICKET

HEAD = re.compile(r"The result for the weekly\s+(.+?)\s+([A-Z]{2})\s*-\s*(\d+)\s+(?:draw\s+)?conducted on\s+(?:[A-Za-z]+day,?\s+)?([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", re.S)
FIRST = re.compile(r"first prize of\s*₹\s*([\d.,]+)\s*(Crore|Lakh)?", re.I)
TIER = re.compile(r"(Consolation|(\d)(?:st|nd|rd|th))\s+prize\s*\(\s*₹\s*([\d,]+)\s*\)\s*:?", re.I)


def amount(num, unit):
    v = float(num.replace(",", ""))
    if unit and unit.lower() == "crore":
        v *= 10_000_000
    elif unit and unit.lower() == "lakh":
        v *= 100_000
    return int(round(v))


def parse_article(text):
    """Return (row, tiers) or raise ValueError."""
    text = re.sub(r"[ \t\xa0]+", " ", text.replace("\u00a0", " "))
    h = HEAD.search(text)
    if not h:
        raise ValueError("draw header not found")
    name, code, no, month, day, year = h.groups()
    date = dt.datetime.strptime(f"{day} {month} {year}", "%d %B %Y").date().isoformat()
    row = {"raw_name": name.strip(), "code": code, "draw_no": int(no), "date": date}

    marks = list(TIER.finditer(text))
    f = FIRST.search(text)
    if not f:
        raise ValueError("1st prize line not found")
    first_seg = text[f.end(): marks[0].start() if marks else len(text)]
    first_tk = TICKET.findall(first_seg)[:1]
    tiers = [{"tier": "1", "amount": amount(f.group(1), f.group(2)),
              "tickets": [{"series": s, "number": n, "place": (p or "").strip().title() or None} for s, n, p in first_tk],
              "endings": []}]
    for i, m in enumerate(marks):
        seg = text[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        tier = "consolation" if m.group(2) is None else m.group(2)
        tks = [{"series": s, "number": n, "place": (p or "").strip().title() or None} for s, n, p in TICKET.findall(seg)]
        tiers.append({"tier": tier, "amount": int(m.group(3).replace(",", "")),
                      "tickets": tks, "endings": [] if tks else ENDING.findall(seg)})
    return row, tiers
