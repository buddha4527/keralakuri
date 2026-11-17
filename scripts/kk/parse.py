"""Parsing of the official pages.

1. The list page (statelottery.kerala.gov.in/index.php/lottery-result-view)
   is an HTML table: NAME(CODE-NO) | DD/MM/YYYY | link to the result page.
2. The result page (result.keralalotteries.com/viewlotisresult.php?drawserial=N)
   lists prizes as text, e.g.
       1st Prize Rs :10000000/-  BV 543398 (PALAKKAD)
       Consolation Prize Rs :5000/-  BN 543398  BO 543398 ...
       4th Prize Rs :5000/-  FOR THE TICKETS ENDING WITH THE FOLLOWING NUMBERS
       1504 2832 3969 ...
We parse the text loosely (regexes, not exact layout), then validate hard.
"""
import html
import re

LIST_ROW = re.compile(
    r"<td[^>]*>\s*([^<]+?)\s*\(\s*([A-Z]{1,3})\s*-\s*(\d+)\s*\)\s*</td>\s*"
    r"<td[^>]*>\s*(\d{2})/(\d{2})/(\d{4})\s*</td>\s*"
    r"<td[^>]*>\s*<a[^>]+href=['\"]([^'\"]+drawserial=(\d+))['\"]",
    re.I,
)


def parse_list_page(page_html):
    """Return newest-first list of draws listed on the official results page."""
    rows = []
    for m in LIST_ROW.finditer(page_html):
        name, code, num, dd, mm, yyyy, url, serial = m.groups()
        rows.append({
            "raw_name": html.unescape(name).strip(),
            "code": code.upper(),
            "draw_no": int(num),
            "date": f"{yyyy}-{mm}-{dd}",
            "source_url": html.unescape(url),
            "drawserial": int(serial),
        })
    return rows


def html_to_text(page_html):
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page_html)
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|tr|td|th|li|h\d)>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t).replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", t)


HEADING = re.compile(
    r"(?P<label>Consolation\s+Prize|(?P<n>\d{1,2})\s*(?:st|nd|rd|th)\s+Prize)"
    r"\s*[-–:]*\s*Rs\.?\s*[:.]?\s*(?P<amt>[\d,]+)\s*/?-?",
    re.I,
)
TICKET = re.compile(r"\b([A-Z]{2})\s?(\d{6})\b(?:\s*\(\s*([A-Za-z .\-]+?)\s*\))?")
ENDING = re.compile(r"(?<![\d/:\-])\b(\d{4})\b(?![\d/:\-])")
FOOTER = re.compile(r"(?i)the prize winners are advised|page\s+\d+\s+of|director|www\.|phone")


def parse_result_text(text):
    """Return list of prize tiers in page order.

    Each tier: {"tier": "1".."9" or "consolation", "amount": int,
                "tickets": [{"series","number","place"}], "endings": ["1234", ...]}
    """
    heads = list(HEADING.finditer(text))
    tiers = []
    for i, h in enumerate(heads):
        seg = text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        f = FOOTER.search(seg)
        if f:
            seg = seg[: f.start()]
        tier = "consolation" if h.group("n") is None else str(int(h.group("n")))
        amount = int(h.group("amt").replace(",", ""))
        tickets = [
            {"series": s, "number": n, "place": (p or "").strip().title() or None}
            for s, n, p in TICKET.findall(seg)
        ]
        endings = [] if tickets else ENDING.findall(seg)
        tiers.append({"tier": tier, "amount": amount, "tickets": tickets, "endings": endings})
    return tiers


class ValidationError(Exception):
    pass


def validate(tiers):
    """Sanity checks before anything is published. Raises ValidationError."""
    by = {t["tier"]: t for t in tiers}
    problems = []
    for need in ("1", "2", "3"):
        if need not in by or not by[need]["tickets"]:
            problems.append(f"{need} prize missing or has no ticket number")
    if "1" in by and by["1"]["tickets"]:
        first = by["1"]["tickets"][0]
        if len(by["1"]["tickets"]) != 1:
            problems.append("1st prize should have exactly one ticket")
        if not first["place"]:
            problems.append("1st prize has no place name")
        cons = by.get("consolation")
        if cons:
            bad = [t for t in cons["tickets"] if t["number"] != first["number"]]
            if bad or not cons["tickets"]:
                problems.append("consolation tickets do not match the 1st prize number")
    ending_tiers = [t for t in tiers if t["endings"]]
    if not ending_tiers:
        problems.append("no 'last 4 digits' prize lists found")
    total = sum(len(t["endings"]) for t in ending_tiers)
    if ending_tiers and total < 50:
        problems.append(f"only {total} last-4-digit numbers found (expected hundreds)")
    for t in ending_tiers:
        if len(set(t["endings"])) != len(t["endings"]):
            problems.append(f"duplicate numbers inside prize {t['tier']}")
    seen = [t["tier"] for t in tiers]
    if len(set(seen)) != len(seen):
        problems.append("a prize tier appears twice")
    for t in tiers:
        if t["amount"] <= 0:
            problems.append(f"prize {t['tier']} has no amount")
    if problems:
        raise ValidationError("; ".join(problems))
    return True
