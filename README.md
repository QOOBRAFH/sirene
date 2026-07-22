# SIRENE — Base locale SIRENE pour Gwanli

Téléchargement mensuel du fichier Stock Établissement INSEE et import dans MariaDB pour les requêtes par commune.

## Prérequis
- Serveur Contabo (4 vCPU, 7.8 Go RAM, 139 Go disque libre)
- MariaDB 10+
- wget, gunzip
- Token Telegram @qoobra_online_bot

## Installation
```bash
./scripts/download.sh    # Téléchargement Stock Établissement
./scripts/import.sh      # Import dans MariaDB
```

## Utilisation
```sql
SELECT * FROM sirene_stock WHERE commune_insee = '34013';
```

## Architecture
```
.
├── scripts/
│   ├── download.sh      # Téléchargement zip INSEE + extraction
│   ├── import.sh        # LOAD DATA INFILE dans MariaDB
│   └── notify.sh        # Notification Telegram @qoobra_online_bot
├── docs/
│   └── schema.sql       # Structure de la table sirene_stock
├── README.md
└── .github/workflows/   # (optionnel) CI/CD
```
