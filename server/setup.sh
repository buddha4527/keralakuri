#!/bin/bash
# One-time setup for the small India server that collects results.
# Run in the server's browser terminal:  bash <(curl -s https://raw.githubusercontent.com/buddha4527/keralakuri/main/server/setup.sh)
set -e
echo "== KeralaKuri server setup =="
export HOME="${HOME:-/root}"
TOKEN="${KK_TOKEN:-}"
if [ -z "$TOKEN" ]; then read -rsp "Paste your GitHub token (it will not show) and press Enter: " TOKEN; echo; fi
sudo apt-get update -qq && sudo apt-get install -y -qq git python3 curl >/dev/null
rm -rf ~/keralakuri
git clone -q "https://x-access-token:${TOKEN}@github.com/buddha4527/keralakuri" ~/keralakuri
cd ~/keralakuri
git config user.name "keralakuri-bot"
git config user.email "buddha4527@users.noreply.github.com"
chmod +x server/run.sh
# Server clock is UTC. 09:00-12:55 UTC = 2:30-6:25 PM in Kerala; 03:00 UTC = 8:30 AM catch-up.
( crontab -l 2>/dev/null | grep -v keralakuri ; \
  echo "*/5 9-12 * * * $HOME/keralakuri/server/run.sh # keralakuri" ; \
  echo "0 3 * * * $HOME/keralakuri/server/run.sh # keralakuri" ) | crontab -
echo
echo "== Testing the official website from this server =="
{
  echo "checked: $(date -u '+%F %T') UTC from $(curl -s -m 10 https://ifconfig.co/country 2>/dev/null || echo unknown)"
  echo "results list: $(curl -s -o /dev/null -m 30 -w '%{http_code}' https://statelottery.kerala.gov.in/index.php/lottery-result-view || echo FAILED)"
  echo "result page:  $(curl -s -o /dev/null -m 30 -w '%{http_code}' 'https://result.keralalotteries.com/viewlotisresult.php?drawserial=75441' 2>&1 || echo FAILED)"
  curl -sv -o /dev/null -m 30 'https://result.keralalotteries.com/viewlotisresult.php?drawserial=75441' 2>&1 | grep -iE 'expire|SSL certificate|verify' | head -5
} | tee data/server-check.txt
git add data/server-check.txt && git commit -qm "Server connection check" && git push -q origin main || true
echo
echo "== First run (loads recent results) =="
python3 scripts/fetch.py --max 30 || true
server/run.sh
echo
echo "Done. The server now checks for new results every 5 minutes from 2:30 to 6:25 PM."
echo "Log file: ~/kk.log"
