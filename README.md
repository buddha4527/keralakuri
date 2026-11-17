# KeralaKuri — Kerala lottery results, made easy to read

A static website (GitHub Pages) that **updates itself** every day:

1. From 3:20 PM to 6:20 PM (IST), every 10 minutes, GitHub Actions opens the official result list at
   `statelottery.kerala.gov.in` and looks for a new draw.
2. When one appears, it downloads the official result page and reads every prize.
3. **Automatic checks** run before anything is published: 1st, 2nd and 3rd prizes present, one 1st prize
   with a place name, consolation numbers equal to the 1st prize number, hundreds of last‑4‑digit numbers,
   no duplicates, right weekday for that lottery, draw number matches.
4. If every check passes → the result is saved in `data/draws/`, the site is rebuilt and published (≈1–2 min).
   If any check fails → **nothing is published** and a GitHub issue called *Result needs review* is opened
   (GitHub emails you).

No server, no database, no monthly bill: the results archive is just the JSON files in `data/draws/`.

## Folder map

| Path | What it is |
|---|---|
| `config.json` | Site name, domain, AdSense ID (empty until approved) |
| `scripts/fetch.py` | Gets, reads and checks official results |
| `scripts/build.py` | Builds every page into `_site/` |
| `scripts/kk/parse.py` | The reading and checking rules |
| `assets/` | `style.css`, `app.js` (ticket checker, My tickets, countdown), logo |
| `data/draws/` | One JSON file per draw — this is your database |
| `data/inbox/` | Manual fallback (see below) |
| `.github/workflows/update.yml` | The daily automation |

## One-time setup

1. Create a new **public** repository on GitHub (e.g. `keralakuri`) and upload all these files.
2. Repository → **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. **Actions** tab → *Update results and publish* → **Run workflow** → backfill `30`.
   This loads the last few weeks of results and publishes the site.
4. Until you buy the domain, set in `config.json`:
   `"site_url": "https://YOURNAME.github.io/keralakuri"`, `"base_path": "/keralakuri/"`, `"custom_domain": ""`.
   After buying `keralakuri.in`: put the domain back in all three, add the DNS records GitHub shows under
   Settings → Pages → Custom domain, and tick **Enforce HTTPS**.

## When a result is held back

You get an email from GitHub. Open the issue to see the reason. Then either:

- **Wait** — often the official page was still half-uploaded; the next run 10 minutes later fixes itself.
  Close the issue once the result is live.
- **Paste it by hand**: on GitHub, open `data/inbox/` → *Add file → Create new file* → name it
  `bt-80.txt`. First line `BT-80 16/11/2026`, then paste the text of the official result page below it.
  Commit. The same checks run on it, and if they pass it is published in about 2 minutes.

## Run on your computer (optional)

```
python3 -m unittest discover -s tests   # parser tests
python3 scripts/build.py --demo         # preview with sample data, opens nothing online
python3 -m http.server -d _site 8000    # then visit http://localhost:8000
```

## Notes

- If the department changes its page layout, the checks fail safely (nothing wrong is published) and you get an issue.
  The rules to adjust are in `scripts/kk/parse.py`.
- GitHub's scheduled runs can start 5–20 minutes late at busy times. For faster updates later, a free
  external scheduler (e.g. cron-job.org) can trigger the workflow through the GitHub API every 5 minutes.
- When AdSense is approved, put your `ca-pub-…` ID in `config.json` → `adsense_client`. The site then adds the
  AdSense script and `ads.txt` automatically.
