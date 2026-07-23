#!/bin/bash
# ============================================
# SIRENE — Librairie partagée
# ============================================

# Configuration
: "${SIRENE_DIR:=$(dirname "$(readlink -f "$0")")/..}"
: "${LOG_FILE:=/var/log/sirene.log}"
: "${DB_HOST:=127.0.0.1}"
: "${DB_PORT:=3306}"
: "${DB_USER:=gwanli}"
: "${DB_PASS:=gwanli_dev_pwd}"
: "${DB_NAME:=sirene_db}"
: "${DATA_DIR:=/srv/sirene/data}"
: "${TELEGRAM_BOT_TOKEN:=}"
: "${TELEGRAM_CHAT_ID:=2059807829}"

# Logger structuré
log() {
    local level="${1:-INFO}"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] $*" | tee -a "$LOG_FILE"
}

info()  { log "INFO" "$*"; }
warn()  { log "WARN" "$*"; }
err()   { log "ERREUR" "$*"; }
ok()    { log "OK" "$*"; }

# Notification Telegram (@qoobra_online_bot)
notify() {
    local msg="$1"
    local token="${TELEGRAM_BOT_TOKEN}"
    local chat_id="${TELEGRAM_CHAT_ID}"
    if [ -z "$token" ]; then
        warn "TELEGRAM_BOT_TOKEN non défini, notification ignorée"
        return
    fi
    curl -s -X POST "https://api.telegram.org/bot${token}/sendMessage" \
        -H "Content-Type: application/json" \
        -d "{\"chat_id\":${chat_id},\"text\":\"${msg}\",\"parse_mode\":\"HTML\"}" \
        --max-time 10 >/dev/null 2>&1 || warn "Échec envoi Telegram"
}

# Vérification MariaDB
db_check() {
    mariadb -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" -p"${DB_PASS}" \
        -e "SELECT 1;" >/dev/null 2>&1
}

# Exécution MariaDB
db_exec() {
    local sql="$1"
    mariadb -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" -p"${DB_PASS}" \
        -e "$sql" 2>&1
}

# Vérification fichier
check_file() {
    local f="$1"
    if [ ! -f "$f" ]; then
        err "Fichier introuvable : $f"
        return 1
    fi
    if [ ! -s "$f" ]; then
        err "Fichier vide : $f"
        return 1
    fi
    return 0
}
