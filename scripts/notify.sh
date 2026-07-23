#!/bin/bash
# ============================================
# SIRENE — Notification Telegram
# Usage : ./notify.sh "message"
# ============================================
set -euo pipefail

SRC_DIR="$(dirname "$(readlink -f "$0")")"
source "${SRC_DIR}/lib.sh"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <message>"
    exit 1
fi

MESSAGE="$1"
notify "📊 SIRENE — ${MESSAGE}"
