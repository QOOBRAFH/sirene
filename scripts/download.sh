#!/bin/bash
# ============================================
# SIRENE — Téléchargement stocks INSEE
# Sources : data.gouv.fr API (URLs stables)
# ============================================
set -euo pipefail

SRC_DIR="$(dirname "$(readlink -f "$0")")"
source "${SRC_DIR}/lib.sh"

DATA_GOUV_API="https://www.data.gouv.fr/api/1/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret"

get_resource_url() {
    local pattern="$1"
    curl -sL "$DATA_GOUV_API" 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
for r in d.get('resources', []):
    title = r.get('title', '').lower()
    fmt = r.get('format', '').lower()
    url = r.get('url', '')
    if '$pattern' in title and fmt == 'zip':
        print(url)
        sys.exit(0)
" 2>/dev/null || true
}

download_file() {
    local name="$1" pattern="$2" dest="$3"
    info "📥 Recherche URL : $name..."
    local url; url=$(get_resource_url "$pattern")
    if [ -z "$url" ]; then
        err "URL non trouvée pour $name (pattern: $pattern)"
        return 1
    fi
    info "📥 Téléchargement $name : $url"
    if curl -sL --retry 3 --retry-delay 10 -o "$dest" "$url" \
        --write-out "%{http_code}" 2>/dev/null | grep -q "200"; then
        local size; size=$(stat -c%s "$dest" 2>/dev/null || echo 0)
        if [ "$size" -gt 1000000 ]; then
            ok "$name : $(numfmt --to=iec $size)"
            return 0
        else
            err "$name : fichier trop petit ($size octets)"
            return 1
        fi
    else
        err "Échec HTTP pour $name"
        return 1
    fi
}

mkdir -p "$DATA_DIR"
cleanup_old() {
    warn "Nettoyage fichiers précédents..."
    rm -f "$DATA_DIR"/*.zip "$DATA_DIR"/*.csv 2>/dev/null || true
}

# Téléchargements
cleanup_old
download_file "StockÉtablissement" "stocketablissement" "${DATA_DIR}/stock-etablissement.zip" || exit 1
download_file "StockUnitéLégale" "stockunitelegale" "${DATA_DIR}/stock-unitelegale.zip" || exit 1

# Extraction
cd "$DATA_DIR"
for f in *.zip; do
    info "📦 Extraction : $f"
    unzip -o "$f" 2>/dev/null || err "Échec extraction $f"
done

# Vérification
CSVS=$(ls *.csv 2>/dev/null | wc -l)
info "📊 CSV extraits : $CSVS fichiers"
ls -lh *.csv 2>/dev/null | awk '{print "  " $5 " " $NF}'
ok "Téléchargement terminé"
