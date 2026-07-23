#!/usr/bin/env python3
"""
SIRENE — Import mensuel des stocks INSEE dans MariaDB (sirene_db).
Pipeline : download → parse → TRUNCATE + LOAD → verify → notify.

Sources :
  StockUniteLegale  (35 colonnes) → table sirene_unite_legale
  StockEtablissement (54 colonnes) → table sirene_etablissement

Utilisation :
  ./import_sirene.py                   # pipeline complet
  ./import_sirene.py --download-only   # seulement téléchargement
  ./import_sirene.py --import-only     # seulement import (fichiers déjà présents)
"""

import argparse
import csv
import os
import sys
import tempfile
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from io import StringIO

# ─── Configuration ────────────────────────────────────────────────────────────
DATA_DIR = Path("/srv/sirene/data")
DB_HOST = os.environ.get("SIRENE_DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("SIRENE_DB_PORT", "3306"))
DB_USER = os.environ.get("SIRENE_DB_USER", "gwanli")
DB_PASS = os.environ.get("SIRENE_DB_PASS", "gwanli_dev_pwd")
DB_NAME = os.environ.get("SIRENE_DB_NAME", "sirene_db")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "2059807829")

DATA_GOUV_API = "https://www.data.gouv.fr/api/1/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret"
CSV_ETAB_FILENAME = "StockEtablissement_utf8.csv"
CSV_UL_FILENAME = "Sirene_StockUniteLegale_utf8.csv"
ZIP_ETAB_FILENAME = "stock-etablissement.zip"
ZIP_UL_FILENAME = "stock-unitelegale.zip"

# ─── Schémas complets ─────────────────────────────────────────────────────────
# Colonne : nom_bd, type_bd, nullable, csv_index

SCHEMA_UNITE_LEGALE = [
    ("siren",                         "VARCHAR(9) NOT NULL PRIMARY KEY",   False),
    ("statut_diffusion",              "VARCHAR(1) DEFAULT NULL",          True),
    ("unite_purgee",                  "VARCHAR(4) DEFAULT NULL",          True),
    ("date_creation",                 "DATE DEFAULT NULL",                True),
    ("sigle",                         "VARCHAR(20) DEFAULT NULL",         True),
    ("sexe",                          "VARCHAR(4) DEFAULT NULL",          True),
    ("prenom_1",                      "VARCHAR(20) DEFAULT NULL",         True),
    ("prenom_2",                      "VARCHAR(20) DEFAULT NULL",         True),
    ("prenom_3",                      "VARCHAR(20) DEFAULT NULL",         True),
    ("prenom_4",                      "VARCHAR(20) DEFAULT NULL",         True),
    ("prenom_usuel",                  "VARCHAR(20) DEFAULT NULL",         True),
    ("pseudonyme",                    "VARCHAR(100) DEFAULT NULL",        True),
    ("identifiant_association",       "VARCHAR(10) DEFAULT NULL",         True),
    ("tranche_effectif",              "VARCHAR(2) DEFAULT NULL",          True),
    ("annee_effectif",                "VARCHAR(4) DEFAULT NULL",          True),
    ("date_dernier_traitement",       "DATETIME DEFAULT NULL",            True),
    ("nombre_periodes",               "INT DEFAULT NULL",                 True),
    ("categorie_entreprise",          "VARCHAR(3) DEFAULT NULL",          True),
    ("annee_categorie_entreprise",    "VARCHAR(4) DEFAULT NULL",          True),
    ("date_debut",                    "DATE DEFAULT NULL",                True),
    ("etat_admin",                    "VARCHAR(1) DEFAULT NULL",          True),
    ("nom",                           "VARCHAR(100) DEFAULT NULL",        True),
    ("nom_usage",                     "VARCHAR(100) DEFAULT NULL",        True),
    ("denomination",                  "VARCHAR(130) DEFAULT NULL",        True),
    ("denomination_usuelle_1",        "VARCHAR(70) DEFAULT NULL",         True),
    ("denomination_usuelle_2",        "VARCHAR(70) DEFAULT NULL",         True),
    ("denomination_usuelle_3",        "VARCHAR(70) DEFAULT NULL",         True),
    ("categorie_juridique",           "VARCHAR(4) DEFAULT NULL",          True),
    ("activite_principale",           "VARCHAR(6) DEFAULT NULL",          True),
    ("nomenclature_activite",         "VARCHAR(8) DEFAULT NULL",          True),
    ("nic_siege",                     "VARCHAR(5) DEFAULT NULL",          True),
    ("economie_sociale_solidaire",    "VARCHAR(1) DEFAULT NULL",          True),
    ("societe_mission",               "VARCHAR(1) DEFAULT NULL",          True),
    ("caractere_employeur",           "VARCHAR(1) DEFAULT NULL",          True),
    ("activite_principale_naf25",     "VARCHAR(6) DEFAULT NULL",          True),
]

SCHEMA_ETABLISSEMENT = [
    ("siren",                            "VARCHAR(9) DEFAULT NULL",           True),
    ("nic",                              "VARCHAR(5) DEFAULT NULL",           True),
    ("siret",                            "VARCHAR(14) NOT NULL PRIMARY KEY",  False),
    ("statut_diffusion",                 "VARCHAR(1) DEFAULT NULL",           True),
    ("date_creation",                    "DATE DEFAULT NULL",                 True),
    ("tranche_effectif",                 "VARCHAR(2) DEFAULT NULL",           True),
    ("annee_effectif",                   "VARCHAR(4) DEFAULT NULL",           True),
    ("activite_registre_metiers",        "VARCHAR(6) DEFAULT NULL",           True),
    ("date_dernier_traitement",          "DATETIME DEFAULT NULL",             True),
    ("est_siege",                        "VARCHAR(5) DEFAULT NULL",           True),
    ("nombre_periodes",                  "INT DEFAULT NULL",                  True),
    ("complement_adresse",               "VARCHAR(100) DEFAULT NULL",         True),
    ("numero_voie",                      "VARCHAR(9) DEFAULT NULL",           True),
    ("indice_repetition",                "VARCHAR(4) DEFAULT NULL",           True),
    ("dernier_numero_voie",              "VARCHAR(9) DEFAULT NULL",           True),
    ("indice_repetition_dernier",        "VARCHAR(4) DEFAULT NULL",           True),
    ("type_voie",                        "VARCHAR(30) DEFAULT NULL",          True),
    ("libelle_voie",                     "VARCHAR(100) DEFAULT NULL",         True),
    ("code_postal",                      "VARCHAR(9) DEFAULT NULL",           True),
    ("libelle_commune",                  "VARCHAR(100) DEFAULT NULL",         True),
    ("libelle_commune_etranger",         "VARCHAR(100) DEFAULT NULL",         True),
    ("distribution_speciale",            "VARCHAR(4) DEFAULT NULL",           True),
    ("code_commune_insee",               "VARCHAR(5) DEFAULT NULL",           True),
    ("code_cedex",                       "VARCHAR(4) DEFAULT NULL",           True),
    ("libelle_cedex",                    "VARCHAR(4) DEFAULT NULL",           True),
    ("code_pays_etranger",               "VARCHAR(5) DEFAULT NULL",           True),
    ("libelle_pays_etranger",            "VARCHAR(100) DEFAULT NULL",         True),
    ("identifiant_adresse",              "VARCHAR(15) DEFAULT NULL",          True),
    ("coordonnee_lambert_x",             "VARCHAR(18) DEFAULT NULL",          True),
    ("coordonnee_lambert_y",             "VARCHAR(18) DEFAULT NULL",          True),
    ("complement_adresse_2",             "VARCHAR(4) DEFAULT NULL",           True),
    ("numero_voie_2",                    "VARCHAR(4) DEFAULT NULL",           True),
    ("indice_repetition_2",              "VARCHAR(4) DEFAULT NULL",           True),
    ("type_voie_2",                      "VARCHAR(4) DEFAULT NULL",           True),
    ("libelle_voie_2",                   "VARCHAR(4) DEFAULT NULL",           True),
    ("code_postal_2",                    "VARCHAR(4) DEFAULT NULL",           True),
    ("libelle_commune_2",                "VARCHAR(100) DEFAULT NULL",         True),
    ("libelle_commune_etranger_2",       "VARCHAR(100) DEFAULT NULL",         True),
    ("distribution_speciale_2",          "VARCHAR(4) DEFAULT NULL",           True),
    ("code_commune_insee_2",             "VARCHAR(5) DEFAULT NULL",           True),
    ("code_cedex_2",                     "VARCHAR(4) DEFAULT NULL",           True),
    ("libelle_cedex_2",                  "VARCHAR(4) DEFAULT NULL",           True),
    ("code_pays_etranger_2",             "VARCHAR(5) DEFAULT NULL",           True),
    ("libelle_pays_etranger_2",          "VARCHAR(100) DEFAULT NULL",         True),
    ("date_debut",                       "DATE DEFAULT NULL",                 True),
    ("etat_admin",                       "VARCHAR(1) DEFAULT NULL",           True),
    ("enseigne_1",                       "VARCHAR(50) DEFAULT NULL",          True),
    ("enseigne_2",                       "VARCHAR(50) DEFAULT NULL",          True),
    ("enseigne_3",                       "VARCHAR(50) DEFAULT NULL",          True),
    ("denomination_usuelle",             "VARCHAR(100) DEFAULT NULL",         True),
    ("activite_principale",              "VARCHAR(6) DEFAULT NULL",           True),
    ("nomenclature_activite",            "VARCHAR(8) DEFAULT NULL",           True),
    ("caractere_employeur",              "VARCHAR(1) DEFAULT NULL",           True),
    ("activite_principale_naf25",        "VARCHAR(6) DEFAULT NULL",           True),
]

# ─── Logger ───────────────────────────────────────────────────────────────────
def log(level, msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)

def info(msg):  log("INFO", msg)
def warn(msg):  log("WARN", msg)
def err(msg):   log("ERREUR", msg)
def ok(msg):    log("OK", msg)

def notify(msg):
    """Envoyer notification Telegram via @qoobra_online_bot."""
    if not TELEGRAM_BOT_TOKEN:
        warn("TELEGRAM_BOT_TOKEN non configuré → notification ignorée")
        return
    import urllib.request
    import json
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }).encode()
    req = urllib.request.Request(url, data=payload,
        headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        warn(f"Échec notification Telegram: {e}")

# ─── Base de données ──────────────────────────────────────────────────────────
def db_connect():
    """Connexion MariaDB via mysql-connector ou pymysql."""
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER,
            password=DB_PASS, charset='utf8mb4',
            autocommit=False, connection_timeout=30
        )
        return conn
    except ImportError:
        import pymysql
        conn = pymysql.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER,
            password=DB_PASS, charset='utf8mb4',
            autocommit=False, connect_timeout=30
        )
        return conn

def init_schema(conn):
    """Créer la base et les tables si elles n'existent pas."""
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.database = DB_NAME

    for table_name, schema in [("sirene_unite_legale", SCHEMA_UNITE_LEGALE),
                                ("sirene_etablissement", SCHEMA_ETABLISSEMENT)]:
        cols = []
        for col_name, col_type, _ in schema:
            cols.append(f"  `{col_name}` {col_type}")
        pk_cols = [c for c, t, n in schema if "PRIMARY KEY" in t]
        if pk_cols:
            cols.append(f"  PRIMARY KEY ({','.join(pk_cols)})")

        create_sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` (\n" + ",\n".join(cols) + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        cur.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        cur.execute(create_sql)
        info(f"Table {table_name} créée")

    # Index additionnels
    indexes = [
        "CREATE INDEX idx_etab_commune ON sirene_etablissement(code_commune_insee)",
        "CREATE INDEX idx_etab_commune_actif ON sirene_etablissement(code_commune_insee, etat_admin)",
        "CREATE INDEX idx_etab_siren ON sirene_etablissement(siren)",
        "CREATE INDEX idx_ul_etat ON sirene_unite_legale(etat_admin)",
        "CREATE INDEX idx_ul_activite ON sirene_unite_legale(activite_principale)",
    ]
    for idx in indexes:
        try:
            cur.execute(idx)
        except Exception:
            pass  # existe déjà
    conn.commit()
    ok("Schéma initialisé")

# ─── Parsing CSV ──────────────────────────────────────────────────────────────
def parse_value(val, col_type):
    """Nettoyer une valeur CSV selon le type de colonne."""
    if val is None or val.strip() == '':
        return None
    val = val.strip().strip('"').strip()
    if val == '':
        return None
    if col_type.startswith("DATE") or col_type.startswith("DATETIME"):
        if val == '' or val == '0000-00-00':
            return None
        return val
    if col_type.startswith("INT"):
        try:
            return int(val)
        except (ValueError, TypeError):
            return None
    if val == '':
        return None
    return val[:int(col_type.split('(')[1].split(')')[0])] if '(' in col_type else val

def parse_csv(filepath, schema, has_header=True):
    """Parser un fichier CSV selon le schéma. Génère des lignes (liste de valeurs)."""
    col_count = len(schema)
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=',', quotechar='"')
        if has_header:
            try:
                next(reader)
            except StopIteration:
                return

        for row in reader:
            # Pad si la ligne est plus courte que le nombre de colonnes
            while len(row) < col_count:
                row.append('')
            # Tronquer si plus longue
            row = row[:col_count]
            yield [parse_value(row[i], schema[i][1]) for i in range(col_count)]

def batch_insert(conn, table_name, schema, rows, batch_size=10000):
    """Insertion par lots avec gestion d'erreur."""
    cur = conn.cursor()
    col_names = [c[0] for c in schema]
    placeholders = ','.join(['%s'] * len(col_names))
    cols_fmt = ','.join([f"`{c}`" for c in col_names])
    sql = f"INSERT INTO `{table_name}` ({cols_fmt}) VALUES ({placeholders})"

    total = 0
    errors = 0
    batch = []

    for row_values in rows:
        batch.append(row_values)
        if len(batch) >= batch_size:
            try:
                cur.executemany(sql, batch)
                total += len(batch)
            except Exception as e:
                errors += len(batch)
                err(f"Erreur batch {table_name}: {e}")
                # Fallback: insérer ligne par ligne
                for r in batch:
                    try:
                        cur.execute(sql, r)
                        total += 1
                    except Exception:
                        errors += 1
            batch = []
            if total % 100000 == 0:
                conn.commit()
                info(f"{table_name} : {total} lignes insérées...")

    # Dernier batch
    if batch:
        try:
            cur.executemany(sql, batch)
            total += len(batch)
        except Exception as e:
            errors += len(batch)
            err(f"Erreur batch final {table_name}: {e}")
            for r in batch:
                try:
                    cur.execute(sql, r)
                    total += 1
                except Exception:
                    errors += 1

    conn.commit()
    return total, errors

# ─── Téléchargement ───────────────────────────────────────────────────────────
def get_resource_url(pattern):
    """Récupérer l'URL stable d'une ressource data.gouv.fr par pattern de titre."""
    import json
    url = DATA_GOUV_API
    req = urllib.request.Request(url, headers={
        "User-Agent": "SIRENE-Import/1.0"
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        err(f"Impossible de contacter data.gouv.fr: {e}")
        return None

    for r in data.get('resources', []):
        title = r.get('title', '').lower()
        fmt = r.get('format', '').lower()
        resource_url = r.get('url', '')
        if pattern in title and fmt == 'zip':
            return resource_url
    return None

def download(name, pattern, dest_zip):
    """Télécharger et extraire un fichier ZIP SIRENE."""
    url = get_resource_url(pattern)
    if not url:
        err(f"URL introuvable pour {name} (pattern: {pattern})")
        return False

    info(f"Téléchargement {name} : {url}")
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "SIRENE-Import/1.0"
        })
        with urllib.request.urlopen(req, timeout=300) as resp:
            with open(dest_zip, 'wb') as f:
                f.write(resp.read())
    except Exception as e:
        err(f"Échec téléchargement {name}: {e}")
        return False

    # Vérifier taille
    size = os.path.getsize(dest_zip)
    if size < 1000000:
        err(f"{name}: fichier trop petit ({size} octets)")
        return False
    ok(f"{name} téléchargé : {size / 1024 / 1024:.1f} Mo")

    # Extraction
    try:
        with zipfile.ZipFile(dest_zip, 'r') as z:
            z.extractall(DATA_DIR)
    except Exception as e:
        err(f"Échec extraction {name}: {e}")
        return False

    csv_files = list(DATA_DIR.glob("*.csv"))
    ok(f"{name} extrait : {len(csv_files)} fichiers CSV")
    return True

# ─── Pipeline ─────────────────────────────────────────────────────────────────
def run_download():
    """Étape 1 : Téléchargement + extraction."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ok = download("StockÉtablissement", "stocketablissement",
                  DATA_DIR / ZIP_ETAB_FILENAME)
    if not ok:
        return False
    ok = download("StockUnitéLégale", "stockunitelegale",
                  DATA_DIR / ZIP_UL_FILENAME)
    return ok

def run_import():
    """Étape 2 : Import des CSV dans MariaDB."""
    conn = db_connect()
    info("Connexion MariaDB OK")
    init_schema(conn)

    results = {}
    for table_name, schema, csv_name in [
        ("sirene_unite_legale", SCHEMA_UNITE_LEGALE, CSV_UL_FILENAME),
        ("sirene_etablissement", SCHEMA_ETABLISSEMENT, CSV_ETAB_FILENAME),
    ]:
        csv_path = DATA_DIR / csv_name
        if not csv_path.exists():
            warn(f"Fichier introuvable : {csv_path}")
            continue

        file_size = os.path.getsize(csv_path) / 1024 / 1024
        info(f"Import {table_name} : {csv_path.name} ({file_size:.1f} Mo)")

        start = time.time()
        rows = parse_csv(csv_path, schema)
        total, errors = batch_insert(conn, table_name, schema, rows)
        elapsed = time.time() - start

        ok(f"{table_name} : {total} lignes OK, {errors} erreurs en {elapsed:.0f}s")
        results[table_name] = {"total": total, "errors": errors, "elapsed": elapsed}

    # Optimisation post-import
    info("🔧 Optimisation des tables...")
    cur = conn.cursor()
    for table in ["sirene_unite_legale", "sirene_etablissement"]:
        try:
            cur.execute(f"OPTIMIZE TABLE `{table}`")
            cur.execute(f"ANALYZE TABLE `{table}`")
        except Exception as e:
            warn(f"Optimisation {table}: {e}")
    conn.commit()

    conn.close()
    return results

def main():
    parser = argparse.ArgumentParser(description="SIRENE — Import mensuel")
    parser.add_argument("--download-only", action="store_true",
                       help="Téléchargement seulement")
    parser.add_argument("--import-only", action="store_true",
                       help="Import seulement (fichiers déjà présents)")
    args = parser.parse_args()

    start_ts = time.time()
    info("🚀 Début pipeline SIRENE mensuel")

    do_download = not args.import_only
    do_import = not args.download_only

    if do_download:
        info("📥 Étape 1/2 : Téléchargement...")
        if not run_download():
            notify("❌ SIRENE — Échec téléchargement (data.gouv.fr)")
            sys.exit(1)
        ok("Téléchargement terminé")

    if do_import:
        info("📦 Étape 2/2 : Import MariaDB...")
        results = run_import()
        if results:
            for table, r in results.items():
                emoji = "✅" if r["errors"] == 0 else "⚠️"
                notify(f"{emoji} SIRENE — {table} : {r['total']} lignes, "
                       f"{r['errors']} erreurs ({r['elapsed']:.0f}s)")

    duration = time.time() - start_ts
    ok(f"Pipeline terminé en {duration:.0f}s")

    if do_download and do_import:
        notify(f"✅ SIRENE — Pipeline mensuel terminé ({duration:.0f}s)")

if __name__ == "__main__":
    main()
