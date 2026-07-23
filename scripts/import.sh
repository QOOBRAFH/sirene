#!/bin/bash
# ============================================
# SIRENE — Import CSV dans MariaDB
# Tables : sirene_etablissement + sirene_unite_legale
# ============================================
set -euo pipefail

SRC_DIR="$(dirname "$(readlink -f "$0")")"
source "${SRC_DIR}/lib.sh"

DATA_DIR="/srv/sirene/data"
CSV_ETAB="${DATA_DIR}/StockEtablissement_utf8.csv"
CSV_UL="${DATA_DIR}/Sirene_StockUniteLegale_utf8.csv"

notify_success() {
    local table="$1" rows="$2"
    notify "✅ SIRENE — Import ${table} terminé : <b>${rows}</b> lignes dans <code>${DB_NAME}.${table}</code>"
}

notify_failure() {
    local table="$1" err="$2"
    notify "❌ SIRENE — Échec import ${table} : ${err}"
}

# ---------- 1. Création base + schéma ----------
info "📦 Création base ${DB_NAME}..."
db_exec "CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

info "📦 Création table sirene_etablissement..."
db_exec "
DROP TABLE IF EXISTS ${DB_NAME}.sirene_etablissement;
CREATE TABLE ${DB_NAME}.sirene_etablissement (
    siren               VARCHAR(9),
    nic                 VARCHAR(5),
    siret               VARCHAR(14) NOT NULL PRIMARY KEY,
    statut_etablissement VARCHAR(1)  DEFAULT NULL,
    code_commune_insee  VARCHAR(5)  DEFAULT NULL,
    code_postal         VARCHAR(5)  DEFAULT NULL,
    activite_principale VARCHAR(6)  DEFAULT NULL,
    date_creation       DATE        DEFAULT NULL,
    etat_admin          VARCHAR(1)  DEFAULT NULL,
    INDEX idx_commune   (code_commune_insee),
    INDEX idx_siren     (siren)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"

info "📦 Création table sirene_unite_legale..."
db_exec "
DROP TABLE IF EXISTS ${DB_NAME}.sirene_unite_legale;
CREATE TABLE ${DB_NAME}.sirene_unite_legale (
    siren               VARCHAR(9) NOT NULL PRIMARY KEY,
    denomination        VARCHAR(255) DEFAULT NULL,
    sigle               VARCHAR(20)  DEFAULT NULL,
    activite_principale VARCHAR(6)   DEFAULT NULL,
    date_creation       DATE         DEFAULT NULL,
    date_derniere_maj   DATE         DEFAULT NULL,
    categorie_entreprise VARCHAR(3)  DEFAULT NULL,
    tranche_effectif    VARCHAR(2)   DEFAULT NULL,
    etat_admin          VARCHAR(1)   DEFAULT NULL,
    INDEX idx_activite  (activite_principale)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"

# ---------- 2. Import Stock Établissement ----------
if [ -f "$CSV_ETAB" ]; then
    info "📥 Import Stock Établissement : $(du -h "$CSV_ETAB" | cut -f1)"
    if db_exec "
        LOAD DATA LOCAL INFILE '${CSV_ETAB}'
        INTO TABLE ${DB_NAME}.sirene_etablissement
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '\"'
        IGNORE 1 LINES
        (siren, nic, siret, statut_etablissement, @dummy1, code_commune_insee,
         code_postal, @dummy2, activite_principale, @dummy3, @dummy4,
         @dummy5, @dummy6, @dummy7, @dummy8, date_creation, @dummy9,
         @dummy10, etat_admin, @dummy11, @dummy12, @dummy13, @dummy14,
         @dummy15);"; then
        rows=$(db_exec "SELECT COUNT(*) FROM ${DB_NAME}.sirene_etablissement;" | tail -1)
        ok "Stock Établissement : ${rows} lignes"
        notify_success "sirene_etablissement" "$rows"
    else
        err "Échec import Stock Établissement"
        notify_failure "sirene_etablissement" "LOAD DATA INFILE failed"
    fi
else
    warn "Fichier Stock Établissement introuvable : ${CSV_ETAB}"
fi

# ---------- 3. Import Stock Unité Légale ----------
if [ -f "$CSV_UL" ]; then
    info "📥 Import Stock Unité Légale : $(du -h "$CSV_UL" | cut -f1)"
    if db_exec "
        LOAD DATA LOCAL INFILE '${CSV_UL}'
        INTO TABLE ${DB_NAME}.sirene_unite_legale
        FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '\"'
        IGNORE 1 LINES
        (siren, @dummy1, @dummy2, denomination, sigle, @dummy3, @dummy4,
         activite_principale, @dummy5, @dummy6, @dummy7, @dummy8,
         @dummy9, @dummy10, date_creation, date_derniere_maj,
         categorie_entreprise, tranche_effectif, etat_admin);"; then
        rows=$(db_exec "SELECT COUNT(*) FROM ${DB_NAME}.sirene_unite_legale;" | tail -1)
        ok "Stock Unité Légale : ${rows} lignes"
        notify_success "sirene_unite_legale" "$rows"
    else
        err "Échec import Stock Unité Légale"
        notify_failure "sirene_unite_legale" "LOAD DATA INFILE failed"
    fi
else
    warn "Fichier Unité Légale introuvable : ${CSV_UL}"
fi

# ---------- 4. Optimisation post-import ----------
info "🔧 Optimisation des tables..."
db_exec "OPTIMIZE TABLE ${DB_NAME}.sirene_etablissement;"
db_exec "OPTIMIZE TABLE ${DB_NAME}.sirene_unite_legale;"
db_exec "ANALYZE TABLE ${DB_NAME}.sirene_etablissement;"
db_exec "ANALYZE TABLE ${DB_NAME}.sirene_unite_legale;"

info "✅ Import SIRENE terminé"
notify "✅ SIRENE — Import mensuel terminé sur Contabo"
