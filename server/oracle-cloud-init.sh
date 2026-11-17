#!/bin/bash
# Paste this whole file into Oracle "Create instance" > Show advanced options > Management > "Paste cloud-init script".
# Replace PASTE_TOKEN_HERE with your GitHub token (github_pat_...). Keep the quotes.
export KK_TOKEN="PASTE_TOKEN_HERE"
export HOME=/root
curl -s https://raw.githubusercontent.com/buddha4527/keralakuri/main/server/setup.sh -o /root/kk-setup.sh
bash /root/kk-setup.sh > /root/kk-setup.log 2>&1
