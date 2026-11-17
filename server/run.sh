#!/bin/bash
# Called by cron. Fetch new results; if any passed the checks, push them to GitHub (GitHub then publishes the site).
exec 9>/tmp/keralakuri.lock; flock -n 9 || exit 0
cd "$HOME/keralakuri" || exit 1
{
  echo "--- $(date -u '+%F %T') UTC"
  git pull -q --rebase origin main
  python3 scripts/fetch.py --max 3
  if [ -n "$(git status --porcelain data/draws)" ]; then
    git add data/draws && git commit -qm "Add result(s) $(date +%F)" && git push -q origin main && echo "pushed new result"
  fi
} >> "$HOME/kk.log" 2>&1
tail -n 2000 "$HOME/kk.log" > "$HOME/kk.log.tmp" && mv "$HOME/kk.log.tmp" "$HOME/kk.log"
