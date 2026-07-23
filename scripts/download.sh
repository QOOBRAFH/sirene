#!/bin/bash
# ============================================
# SIRENE — Téléchargement Stock Établissement INSEE
# Source : data.gouv.fr ou insee.fr
# ============================================
set -euo pipefail

: "${SRC_DIR:=$(dirname "$(readlink -f "$0")")/..}"  # racine projet
source "${SRC_DIR}/scripts/lib.sh" 2>/dev/null || true

DEST="/srv/sirene/data"
mkdir -p "$DEST"
LOG_FILE="/var/log/sirene-download.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
err() { log "❌ ERREUR: $*"; }

# 1️⃣ Stock Établissement
FILE_ETAB="StockEtablissement_utf8.zip"
URL_ETAB="https://www.insee.fr/fr/statistiques/fichier/${FILE_ETAB}"

log "📥 Téléchargement $FILE_ETAB..."
if wget -q --timeout=300 --tries=3 "$URL_ETAB" -O "${DEST}/${FILE_ETAB}"; then
    log "✅ Stock Établissement : $(du -h "${DEST}/${FILE_ETAB}" | cut -f1)"
else
    # Fallback data.gouv.fr
    URL_ETAB_FB=$(curl -sL "https://www.data.gouv.fr/api/1/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-sous-format-csv/" | \
        python3 -c "import sys,json; d=json.load(sys.stdin); r=[r for r in d.get('resources',[]) if 'StockEtablissement' in r.get('title','') and r.get('format')=='zip']; print(r[0]['url'] if r else '')" 2>/dev/null)
    if [ -n "$URL_ETAB_FB" ]; then
        log "⚠️ Fallback data.gouv.fr : $URL_ETAB_FB"
        wget -q --timeout=300 --tries=3 "$URL_ETAB_FB" -O "${DEST}/${FILE_ETAB}" || err "Échec fallback"
    else
        err "Impossible de télécharger $FILE_ETAB"
        exit 1
    fi
fi

# 2️⃣ Stock Unité Légale
FILE_UL="Sirene_StockUniteLegale_utf8.zip"
URL_UL="https://www.insee.fr/fr/statistiques/fichier/${FILE_UL}"

log "📥 Téléchargement $FILE_UL..."
if wget -q --timeout=300 --tries=3 "$URL_UL" -O "${DEST}/${FILE_UL}"; then
    log "✅ Unité Légale : $(du -h "${DEST}/${FILE_UL}" | cut -f1)"
else
    err "Impossible de télécharger $FILE_UL"
    # Non fatal — on continue
fi

# 3️⃣ Extraction
log "📦 Extraction des CSV..."
cd "$DEST"
for f in *.zip; do
    if [ -f "$f" ]; then
        unzip -o "$f" 2>/dev/null && log "✅ Extrait : $f" || err "Échec extraction $f"
    fi
done

log "✅ Téléchargement terminé"
ls -lh "$DEST"/*.csv 2>/dev/null | awk '{print $5, $NF}'
