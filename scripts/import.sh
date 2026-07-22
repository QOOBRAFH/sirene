#!/bin/bash
# Import Stock Établissement dans MariaDB
set -euo pipefail

DB_NAME="${1:-sirene_db}"
CSV_FILE="/srv/sirene/data/StockEtablissement_utf8.csv"

if [ ! -f "$CSV_FILE" ]; then
    echo "❌ Fichier introuvable : $CSV_FILE"
    exit 1
fi

echo "📦 Import dans MariaDB (base: $DB_NAME)..."

mariadb -u root -e "
CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

DROP TABLE IF EXISTS ${DB_NAME}.sirene_stock;

CREATE TABLE ${DB_NAME}.sirene_stock (
    siren VARCHAR(9),
    nic VARCHAR(5),
    siret VARCHAR(14) PRIMARY KEY,
    statut_etablissement VARCHAR(1),
    code_commune_insee VARCHAR(5),
    INDEX idx_commune (code_commune_insee),
    activite_principale VARCHAR(6),
    denomination VARCHAR(255),
    code_postal VARCHAR(5),
    date_creation DATE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

LOAD DATA INFILE '$CSV_FILE'
INTO TABLE ${DB_NAME}.sirene_stock
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '\"'
IGNORE 1 LINES;
"

echo "✅ Import terminé"
echo "Lignes : $(mariadb -N -e 'SELECT COUNT(*) FROM '${DB_NAME}'.sirene_stock')"
