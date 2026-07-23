#!/bin/bash
# ============================================
# SIRENE — Pipeline mensuel complet
# Télécharge + extrait + importe les stocks INSEE
# ============================================
set -euo pipefail

SRC_DIR="$(dirname "$(readlink -f "$0")")"
source "${SRC_DIR}/lib.sh"

START_TS=$(date +%s)
info "🚀 Début pipeline SIRENE mensuel"

# 1. Téléchargement
info "📥 Étape 1/4 : Téléchargement..."
"${SRC_DIR}/download.sh" || {
    err "Échec téléchargement"
    notify "❌ SIRENE — Échec téléchargement (data.gouv.fr / insee.fr)"
    exit 1
}

# 2. Vérification fichiers
info "🔍 Étape 2/4 : Vérification..."
CSV_ETAB="${DATA_DIR}/StockEtablissement_utf8.csv"
CSV_UL="${DATA_DIR}/Sirene_StockUniteLegale_utf8.csv"
check_file "$CSV_ETAB" || exit 1

# 3. Import
info "📦 Étape 3/4 : Import MariaDB..."
"${SRC_DIR}/import.sh" || {
    err "Échec import"
    notify "❌ SIRENE — Échec import MariaDB"
    exit 1
}

# 4. Nettoyage vieux fichiers (garder la version précédente)
info "🧹 Étape 4/4 : Nettoyage..."
find "$DATA_DIR" -name "*.csv" -mtime +2 -delete
find "$DATA_DIR" -name "*.zip" -mtime +2 -delete

DURATION=$(( $(date +%s) - START_TS ))
ok "Pipeline terminé en ${DURATION}s"

notify "✅ SIRENE — Pipeline mensuel terminé (${DURATION}s)"
