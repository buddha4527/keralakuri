#!/usr/bin/env python3
"""Build the static website into _site/ from data/draws/*.json.

    python scripts/build.py          # real build
    python scripts/build.py --demo   # preview with the sample test result (never deployed)
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import pathlib
import shutil
import sys
import urllib.parse
from collections import OrderedDict

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from kk.lotteries import DAY_NAMES, WEEKLY, slugify  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config.json").read_text())
OUT = ROOT / "_site"
BASE = CFG["base_path"].rstrip("/") + "/"
SITE = CFG["site_url"].rstrip("/")
NAME = CFG["site_name"]
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
e = html.escape


# ---------- helpers ----------
def rupees(n):
    if n >= 10_000_000:
        v = n / 10_000_000
        return f"₹{v:g} Crore"
    if n >= 100_000:
        return f"₹{n / 100_000:g} Lakh"
    s = str(n)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return "₹" + s


def ordinal(t):
    if t == "consolation":
        return "Consolation prize"
    n = int(t)
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n, 'th') } prize"


def nice_date(iso, fmt="%A, %-d %B %Y"):
    return dt.date.fromisoformat(iso).strftime(fmt)


def dmy(iso, sep="-"):
    y, m, d = iso.split("-")
    return f"{d}{sep}{m}{sep}{y}"


def url(path):
    return BASE + path.lstrip("/")


def abs_url(path):
    return SITE + "/" + path.lstrip("/")


def tier(draw, t):
    return next((x for x in draw["tiers"] if x["tier"] == t), None)


def tk(t):
    return f"{t['series']} {t['number']}"


LOGO = ('<svg width="36" height="24" viewBox="0 0 120 80" aria-hidden="true"><defs><mask id="lm">'
        '<rect width="120" height="80" fill="#fff"/><circle cx="0" cy="40" r="11"/><circle cx="120" cy="40" r="11"/>'
        '</mask></defs><rect width="120" height="80" rx="14" fill="#0B6E4F" mask="url(#lm)"/>'
        '<line x1="36" y1="12" x2="36" y2="68" stroke="#FFF9EE" stroke-width="3" stroke-dasharray="4 6" '
        'stroke-linecap="round" opacity=".55"/><circle cx="76" cy="40" r="20" fill="#F4B400"/>'
        '<path d="M66 40l7 7 13-14" fill="none" stroke="#14211B" stroke-width="5" stroke-linecap="round" '
        'stroke-linejoin="round"/></svg>')


def asset_ver():
    h = hashlib.md5()
    for f in ("style.css", "app.js"):
        h.update((ROOT / "assets" / f).read_bytes())
    return h.hexdigest()[:8]


VER = asset_ver()


def layout(path, title, desc, body, jsonld=None, demo=False):
    canonical = abs_url(path)
    ld = "".join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in (jsonld or []))
    ads = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={e(CFG["adsense_client"])}" crossorigin="anonymous"></script>'
           if CFG.get("adsense_client") and not demo else "")
    banner = ('<div style="background:#14211B;color:#fff;text-align:center;font-size:13px;padding:6px">'
              'PREVIEW — sample data from the test file, not a real result</div>') if demo else ""
    robots = '<meta name="robots" content="noindex">' if demo else ""
    return f"""<!doctype html>
<html lang="en" data-base="{BASE}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canonical}">
{robots}
<meta property="og:type" content="website"><meta property="og:site_name" content="{NAME}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{canonical}">
<meta name="theme-color" content="#0B6E4F">
<link rel="icon" href="{url('assets/favicon.svg')}" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Baloo+Chettan+2:wght@700;800&family=JetBrains+Mono:wght@700;800&display=swap">
<link rel="stylesheet" href="{url('assets/style.css')}?v={VER}">
{ads}{ld}
</head>
<body>
{banner}
<header class="top"><div class="wrap">
<a class="brand" href="{url('')}">{LOGO}<span>Kerala<b>Kuri</b></span></a>
<nav><a href="{url('results/')}">Results</a><a href="{url('')}#check">Check</a></nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">
<nav><a href="{url('about/')}">About</a><a href="{url('how-to-claim/')}">How to claim</a><a href="{url('disclaimer/')}">Disclaimer</a><a href="{url('privacy/')}">Privacy</a><a href="{url('contact/')}">Contact</a></nav>
<p>{NAME} is an independent results website. It is not run by, or connected with, the Directorate of Kerala State Lotteries. Results are taken from the official website; the Kerala Government Gazette is final. Official site: <a href="{CFG['official_site']}" rel="nofollow">{CFG['official_site'].split('//')[1]}</a></p>
</div></footer>
<script src="{url('assets/app.js')}?v={VER}" defer></script>
</body>
</html>
"""


def week_strip():
    cells = []
    order = ["SM", "BT", "SS", "DL", "KN", "SK", "KR"]
    for code in order:
        w = WEEKLY[code]
        cells.append(f'<a href="{url("lottery/" + slugify(w["name"]) + "/")}" data-wd="{w["weekday"]}" title="{w["name"]} — every {DAY_NAMES[w["weekday"]]}">'
                     f'<span>{DAY_NAMES[w["weekday"]][:3]}</span>{code}</a>')
    return ('<nav class="week" aria-label="Lottery for each day">' + "".join(cells) + "</nav>"
            '<script>(function(){var d=new Date(Date.now()+(new Date().getTimezoneOffset()+330)*6e4),w=(d.getDay()+6)%7,'
            'a=document.querySelector(\'.week a[data-wd="\'+w+\'"]\');if(a){a.classList.add("today");a.setAttribute("aria-current","date")}})()</script>')


def share_link(draw, path):
    f = tier(draw, "1")["tickets"][0]
    text = (f"Kerala lottery {draw['name']} {draw['code']}-{draw['draw_no']} ({dmy(draw['date'], '.')})\n"
            f"1st prize {rupees(tier(draw, '1')['amount'])}: {tk(f)}\nCheck your ticket: {abs_url(path)}")
    return "https://wa.me/?text=" + urllib.parse.quote(text)


def draw_block(draw, path, heading, home=False):
    first = tier(draw, "1")
    f = first["tickets"][0]
    parts = [f'<div style="margin-top:14px"><span class="pill">Official result</span></div>',
             f'<h1 style="margin-top:8px">{heading}</h1>',
             f'<p class="meta">{e(draw["name"])} {draw["code"]}-{draw["draw_no"]} · {nice_date(draw["date"])} · Draw at 3:00 PM</p>',
             f'<section class="first" aria-label="First prize"><div class="row"><span class="label">1st prize</span><span class="amt">{rupees(first["amount"])}</span></div>'
             f'<div class="big">{tk(f)}</div>'
             f'<div class="row"><span>{"Sold at " + e(f["place"]) if f.get("place") else ""}</span><button type="button" data-copy="{tk(f)}">Copy number</button></div></section>']
    tops = [tier(draw, t) for t in ("2", "3") if tier(draw, t)]
    if tops:
        cards = []
        for t in tops:
            for k in t["tickets"]:
                cards.append(f'<section class="card"><div class="label">{ordinal(t["tier"])} · {rupees(t["amount"])}</div>'
                             f'<div class="tk">{tk(k)}</div><div class="place">{e(k["place"] or "")}</div></section>')
        parts.append('<div class="two">' + "".join(cards) + "</div>")
    cons = tier(draw, "consolation")
    if cons:
        parts.append(f'<section class="card" style="margin-top:12px"><b>Consolation prize · {rupees(cons["amount"])}</b>'
                     f'<div class="hint">Same number as the 1st prize in every other series: <b style="font-family:var(--mono);color:var(--ink)">{f["number"]}</b></div></section>')
    parts.append(f'<div class="actions"><a class="btn" href="#check">Check my ticket</a>'
                 f'<a class="btn ghost" href="{share_link(draw, path)}" rel="nofollow noopener" target="_blank">Share on WhatsApp</a></div>')
    parts.append(f'''<section class="check" id="check" aria-labelledby="check-h">
<h2 id="check-h" style="margin:0 0 10px">Check your ticket</h2>
<form id="check-form" autocomplete="off"><label for="ticket">Ticket number for {e(draw["code"])}-{draw["draw_no"]}</label>
<input id="ticket" name="ticket" placeholder="{f['series']} 000000" inputmode="text" maxlength="9" required>
<div class="row"><span class="hint">Two letters and six digits, as printed on your ticket.</span><button class="btn" style="width:auto;padding:0 22px" type="submit">Check</button></div></form>
<div class="out" id="check-out" role="status" aria-live="polite"></div></section>''')
    lower = [t for t in draw["tiers"] if t["tier"] not in ("1", "2", "3", "consolation")]
    if lower:
        parts.append('<h2>Other prizes</h2><p class="hint">Matched on the <b>last 4 digits</b> of your ticket number.</p>')
        for t in lower:
            if t["endings"]:
                nums = "".join(f'<span data-n="{n}">{n}</span>' for n in t["endings"])
                count = f'{len(t["endings"])} numbers'
            else:
                nums = "".join(f'<span style="grid-column:span 2">{tk(k)}</span>' for k in t["tickets"])
                count = f'{len(t["tickets"])} tickets'
            parts.append(f'<details class="tier"{" open" if t["tier"] == "4" else ""}><summary><span>{ordinal(t["tier"])} · {rupees(t["amount"])}</span>'
                         f'<span class="hint">{count}</span></summary><div class="nums">{nums}</div></details>')
    parts.append(f'<div class="note"><b>Before you claim:</b> check your ticket against the Kerala Government Gazette and surrender it within 30 days of the draw. '
                 f'<a href="{url("how-to-claim/")}">How to claim</a> · <a href="{e(draw.get("source_url") or CFG["official_site"])}" rel="nofollow">Official result</a></div>')
    data = {k: draw[k] for k in ("code", "draw_no", "name", "date", "tiers")}
    parts.append(f'<script type="application/json" id="kk-draw">{json.dumps(data, separators=(",", ":"))}</script>')
    return "\n".join(parts)


def draw_list(draws):
    rows = []
    for d in draws:
        f = tier(d, "1")["tickets"][0]
        rows.append(f'<a href="{url("result/" + d["slug"] + "/")}"><span><b>{e(d["name"])} {d["code"]}-{d["draw_no"]}</b>'
                    f'<small>{nice_date(d["date"], "%a, %-d %b %Y")}</small></span><span class="tkn">{tk(f)}</span></a>')
    return '<div class="list">' + "".join(rows) + "</div>"


def org_ld():
    return {"@context": "https://schema.org", "@type": "Organization", "name": NAME, "url": SITE + "/",
            "logo": abs_url("assets/favicon.svg")}


def crumbs(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": abs_url(p)} for i, (n, p) in enumerate(items)]}


def write(path, content):
    p = OUT / path
    if path.endswith("/") or path == "":
        p = p / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


# ---------- pages ----------
FAQ = [
    ("What time is the Kerala lottery result?", "The draw is held every day at 3:00 PM in Thiruvananthapuram. The official result is usually published by about 4 PM, and this page updates on its own as soon as it is out."),
    ("Which lottery is drawn today?", "Sunday Samrudhi (SM), Monday Bhagyathara (BT), Tuesday Sthree Sakthi (SS), Wednesday Dhanalekshmi (DL), Thursday Karunya Plus (KN), Friday Suvarna Keralam (SK), Saturday Karunya (KR)."),
    ("How do I check my ticket?", "Type the two letters and six digits from your ticket into the box above. Lower prizes are matched on the last four digits."),
    ("How long do I have to claim a prize?", "Winning tickets must be surrendered within 30 days of the draw, after checking them against the Kerala Government Gazette."),
]


def home(draws, demo):
    body = [week_strip(), '<div class="countdown" id="countdown" role="status"></div>']
    if draws:
        latest = draws[0]
        body.append(draw_block(latest, "", "Kerala Lottery Result Today", home=True))
        title = f"Kerala Lottery Result Today {dmy(latest['date'], '.')} – {latest['name']} {latest['code']}-{latest['draw_no']} | {NAME}"
        f = tier(latest, "1")["tickets"][0]
        desc = (f"Kerala lottery result today: {latest['name']} {latest['code']}-{latest['draw_no']} ({dmy(latest['date'], '.')}). "
                f"1st prize {rupees(tier(latest, '1')['amount'])} {tk(f)}. Full list and instant ticket check.")
    else:
        body.append('<h1 style="margin-top:14px">Kerala Lottery Result Today</h1><p class="meta">The next result appears here automatically after the 3 PM draw.</p>')
        title, desc = f"Kerala Lottery Result Today – Live 3 PM Result | {NAME}", "Today's Kerala lottery result, easy to read, with an instant ticket checker."
    body.append('''<section class="check" id="my-tickets" aria-labelledby="my-h"><h2 id="my-h" style="margin:0 0 4px">My tickets</h2>
<p class="hint" style="margin:0 0 10px">Save your ticket now — it is checked automatically when the result is out. Saved only on this phone.</p>
<form id="my-form" autocomplete="off"><label for="my-ticket">Ticket number</label><input id="my-ticket" placeholder="AB 123456" maxlength="9">
<div class="row"><select id="my-draw" aria-label="Draw date" style="height:48px;border-radius:12px;border:1px solid var(--line);padding:0 10px;font:inherit;background:#fff;min-width:0"></select>
<button class="btn" style="width:auto;padding:0 18px" type="submit">Save</button></div></form>
<p class="hint" id="my-empty">No saved tickets yet.</p><ul class="mine" id="my-list"></ul></section>''')
    if len(draws) > 1:
        body.append("<h2>Recent results</h2>" + draw_list(draws[1:11]) +
                    f'<p><a href="{url("results/")}">All past results →</a></p>')
    body.append("<h2>Questions</h2>" + "".join(f"<h3 style='font-size:18px;margin:16px 0 4px'>{e(q)}</h3><p style='margin:0'>{e(a)}</p>" for q, a in FAQ))
    ld = [org_ld(), {"@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": SITE + "/"},
          {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
              {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]}]
    write("", layout("", title, desc, "\n".join(body), ld, demo))


def draw_page(d, demo):
    path = f"result/{d['slug']}/"
    f = tier(d, "1")["tickets"][0]
    title = f"Kerala Lottery Result {dmy(d['date'], '.')} – {d['name']} {d['code']}-{d['draw_no']} | {NAME}"
    desc = (f"{d['name']} {d['code']}-{d['draw_no']} result, {nice_date(d['date'])}: 1st prize {rupees(tier(d, '1')['amount'])} "
            f"{tk(f)}{' (' + f['place'] + ')' if f.get('place') else ''}. Full prize list and ticket checker.")
    lslug = slugify(d["name"])
    body = (f'<p class="hint" style="margin:14px 0 0"><a href="{url("")}">Home</a> › <a href="{url("lottery/" + lslug + "/")}">{e(d["name"])}</a> › {d["code"]}-{d["draw_no"]}</p>'
            + draw_block(d, path, f"{e(d['name'])} {d['code']}-{d['draw_no']} Result"))
    ld = [crumbs([("Home", ""), (d["name"], f"lottery/{lslug}/"), (f"{d['code']}-{d['draw_no']}", path)]),
          {"@context": "https://schema.org", "@type": "Article", "headline": f"{d['name']} {d['code']}-{d['draw_no']} result {dmy(d['date'], '.')}",
           "datePublished": d.get("fetched_at"), "dateModified": d.get("fetched_at"), "mainEntityOfPage": abs_url(path),
           "author": {"@type": "Organization", "name": NAME}, "publisher": org_ld()}]
    write(path, layout(path, title, desc, body, ld, demo))


def lottery_pages(draws, demo):
    groups = OrderedDict()
    for code, w in WEEKLY.items():
        groups[slugify(w["name"])] = {"name": w["name"], "code": code, "weekday": w["weekday"], "draws": []}
    for d in draws:
        s = slugify(d["name"])
        groups.setdefault(s, {"name": d["name"], "code": d["code"], "weekday": None, "draws": []})["draws"].append(d)
    for s, g in groups.items():
        path = f"lottery/{s}/"
        when = f"every {DAY_NAMES[g['weekday']]} at 3:00 PM" if g["weekday"] is not None else "on its announced date at 3:00 PM"
        body = (f'<h1 style="margin-top:18px">{e(g["name"])} ({g["code"]}) Lottery Result</h1>'
                f'<p class="meta">{e(g["name"])} is drawn {when}. Latest results first.</p>'
                + (draw_list(g["draws"]) if g["draws"] else '<p>No results stored yet. The next draw will appear here automatically.</p>'))
        title = f"{g['name']} {g['code']} Lottery Result Today & Past Results | {NAME}"
        desc = f"All {g['name']} ({g['code']}) Kerala lottery results — drawn {when}. Latest result, full prize lists and ticket checker."
        write(path, layout(path, title, desc, body, [crumbs([("Home", ""), (g["name"], path)])], demo))
    return list(groups.keys())


def archive(draws, demo):
    by_month = OrderedDict()
    for d in draws:
        by_month.setdefault(nice_date(d["date"], "%B %Y"), []).append(d)
    body = ['<h1 style="margin-top:18px">Past Kerala Lottery Results</h1><p class="meta">Every draw we have published, newest first.</p>', week_strip()]
    for m, ds in by_month.items():
        body.append(f"<h2>{m}</h2>" + draw_list(ds))
    if not draws:
        body.append("<p>No results yet.</p>")
    write("results/", layout("results/", f"Kerala Lottery Results – All Past Results | {NAME}",
                             "Full archive of Kerala State lottery results with 1st prize numbers and full prize lists.", "\n".join(body), None, demo))


STATIC = {
    "about/": ("About KeralaKuri", f"""<p>{NAME} shows the Kerala State lottery result in a clean, fast page that is easy to read on a phone, with a ticket checker so you do not have to scan long lists of numbers.</p>
<p>Results are collected automatically from the official website of the Directorate of Kerala State Lotteries soon after they are published, checked for errors, and then shown here. If anything looks wrong, the result is held back until it has been checked by hand.</p>
<p>We are an independent website. We do not sell tickets and we are not connected with the Kerala government.</p>"""),
    "how-to-claim/": ("How to claim a Kerala lottery prize", f"""<p>This is a short summary. Always follow the instructions from the Directorate of Kerala State Lotteries.</p>
<h2>1. Check against the Gazette</h2><p>Check your ticket number against the result published in the Kerala Government Gazette. Websites, including this one, are only a convenience.</p>
<h2>2. Claim within 30 days</h2><p>Winning tickets must be surrendered within 30 days of the draw date.</p>
<h2>3. Where to claim</h2><p>Smaller prizes can be claimed at district lottery offices and sub-offices. Larger prizes are claimed through the Directorate of State Lotteries or a bank, with identity documents.</p>
<h2>4. Tax</h2><p>Large prizes are paid after tax is deducted at source, so the amount you receive is less than the prize amount.</p>
<p><a href="{CFG['official_site']}" rel="nofollow">Official website of Kerala State Lotteries</a></p>"""),
    "disclaimer/": ("Disclaimer", f"""<p>{NAME} publishes Kerala State lottery results for information only. While we check every result automatically before showing it, mistakes are possible.</p>
<p>The result published in the Kerala Government Gazette is the only final result. Please verify your ticket there before claiming any prize.</p>
<p>{NAME} is not connected with the Directorate of Kerala State Lotteries or the Government of Kerala, does not sell lottery tickets and does not encourage gambling. Lotteries are legal only in some Indian states; follow the law where you live.</p>"""),
    "privacy/": ("Privacy policy", f"""<p>{NAME} does not ask for your name, phone number or email.</p>
<p><b>Ticket checker and My tickets.</b> The ticket numbers you type are checked inside your browser. Saved tickets are stored only on your own device (local storage) and are never sent to us.</p>
<p><b>Advertising and analytics.</b> We may show ads from Google AdSense and use privacy-friendly analytics. Google and its partners may use cookies to show ads based on your visits to this and other websites. You can turn off personalised ads at <a href="https://adssettings.google.com" rel="nofollow">Google Ad Settings</a>.</p>
<p>Questions: {e(CFG['contact_email'])}</p>"""),
    "contact/": ("Contact", f"""<p>Found a mistake in a result, or have a suggestion? Email <a href="mailto:{e(CFG['contact_email'])}">{e(CFG['contact_email'])}</a>.</p>
<p>We cannot help with prize claims — please contact the Directorate of Kerala State Lotteries for that.</p>"""),
}


def static_pages(demo):
    for path, (h, content) in STATIC.items():
        write(path, layout(path, f"{h} | {NAME}", f"{h} — {NAME}, Kerala lottery results.",
                           f'<article class="prose"><h1 style="margin-top:18px">{e(h)}</h1>{content}</article>', None, demo))
    write("404.html", layout("404.html", f"Page not found | {NAME}", "Page not found.",
                             f'<h1 style="margin-top:18px">Page not found</h1><p><a href="{url("")}">See today’s result →</a></p>', None, demo))


def seo_files(draws, lotteries, demo):
    today = dt.datetime.now(IST).date().isoformat()
    urls = [("", draws[0]["date"] if draws else today), ("results/", draws[0]["date"] if draws else today)]
    urls += [(f"lottery/{s}/", today) for s in lotteries]
    urls += [(f"result/{d['slug']}/", d["date"]) for d in draws]
    urls += [(p, "2026-11-17") for p in STATIC]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"<url><loc>{abs_url(p)}</loc><lastmod>{m}</lastmod></url>" for p, m in urls]
    sm.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(sm))
    (OUT / "robots.txt").write_text(("User-agent: *\nDisallow: /\n" if demo else "User-agent: *\nAllow: /\n") + f"Sitemap: {abs_url('sitemap.xml')}\n")
    if CFG.get("custom_domain") and not demo:
        (OUT / "CNAME").write_text(CFG["custom_domain"] + "\n")
    if CFG.get("adsense_client") and not demo:
        pub = CFG["adsense_client"].replace("ca-", "")
        (OUT / "ads.txt").write_text(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")
    (OUT / ".nojekyll").write_text("")
    (OUT / "data").mkdir(exist_ok=True)
    slim = [{k: d[k] for k in ("code", "draw_no", "name", "date", "slug", "tiers")} for d in draws[:14]]
    (OUT / "data" / "recent.json").write_text(json.dumps(slim, separators=(",", ":")))


def load_draws(demo):
    if demo:
        sys.path.insert(0, str(ROOT / "scripts"))
        from kk.parse import html_to_text, parse_result_text
        tiers = parse_result_text(html_to_text((ROOT / "tests/fixtures/result_sample.html").read_text()))
        return [{"code": "BT", "draw_no": 80, "name": "Bhagyathara", "date": "2026-11-16", "slug": "bhagyathara-bt-80-16-11-2026",
                 "source_url": None, "fetched_at": "2026-11-16T16:05:00+05:30", "tiers": tiers}]
    draws = [json.loads(p.read_text()) for p in (ROOT / "data" / "draws").glob("*.json")]
    return sorted(draws, key=lambda d: (d["date"], d["draw_no"]), reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets")
    draws = load_draws(a.demo)
    home(draws, a.demo)
    for d in draws:
        draw_page(d, a.demo)
    lots = lottery_pages(draws, a.demo)
    archive(draws, a.demo)
    static_pages(a.demo)
    seo_files(draws, lots, a.demo)
    print(f"built {len(draws)} result pages into {OUT}")


if __name__ == "__main__":
    main()
