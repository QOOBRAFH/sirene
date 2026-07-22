#!/bin/bash
# Télécharge le fichier Stock Établissement INSEE
# Source : https://www.insee.fr/fr/information/2407703
set -euo pipefail

URL_BASE="https://www.insee.fr/fr/statistiques/fichier"
FILE="StockEtablissement_utf8.zip"
DEST_DIR="/srv/sirene/data"

mkdir -p "$DEST_DIR"
echo "📥 Téléchargement $FILE..."
wget -q "$URL_BASE/$FILE" -O "$DEST_DIR/$FILE"
echo "✅ Téléchargé : $(du -h "$DEST_DIR/$FILE" | cut -f1)"

echo "📦 Extraction..."
cd "$DEST_DIR"
unzip -o "$FILE"
echo "✅ Extrait"

echo "🔍 Fichiers :"
ls -lh "$DEST_DIR"/*.csv 2>/dev/null || ls -lh "$DEST_DIR"/
