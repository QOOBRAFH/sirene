#!/bin/bash
# Envoie une notification Telegram via @qoobra_online_bot
set -euo pipefail

TOKEN="{{TELEGRAM_BOT_TOKEN}}"
CHAT_ID="2059807829"
MESSAGE="$1"

curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\":$CHAT_ID,\"text\":\"$MESSAGE\",\"parse_mode\":\"HTML\"}" > /dev/null
