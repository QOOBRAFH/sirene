-- ============================================
-- SIRENE — Schéma MariaDB
-- ============================================

-- Base dédiée
CREATE DATABASE IF NOT EXISTS sirene_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Stock Établissement (43M+ lignes)
CREATE TABLE IF NOT EXISTS sirene_db.sirene_etablissement (
    siren               VARCHAR(9)      DEFAULT NULL,
    nic                 VARCHAR(5)      DEFAULT NULL,
    siret               VARCHAR(14)     NOT NULL PRIMARY KEY,
    statut_etablissement VARCHAR(1)     DEFAULT NULL,
    code_commune_insee  VARCHAR(5)      DEFAULT NULL,
    code_postal         VARCHAR(5)      DEFAULT NULL,
    activite_principale VARCHAR(6)      DEFAULT NULL,
    date_creation       DATE            DEFAULT NULL,
    etat_admin          VARCHAR(1)      DEFAULT NULL,
    INDEX idx_commune   (code_commune_insee),
    INDEX idx_siren     (siren)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Stock Unité Légale
CREATE TABLE IF NOT EXISTS sirene_db.sirene_unite_legale (
    siren                VARCHAR(9)     NOT NULL PRIMARY KEY,
    denomination         VARCHAR(255)   DEFAULT NULL,
    sigle                VARCHAR(20)    DEFAULT NULL,
    activite_principale  VARCHAR(6)     DEFAULT NULL,
    date_creation        DATE           DEFAULT NULL,
    date_derniere_maj    DATE           DEFAULT NULL,
    categorie_entreprise VARCHAR(3)     DEFAULT NULL,
    tranche_effectif     VARCHAR(2)     DEFAULT NULL,
    etat_admin           VARCHAR(1)     DEFAULT NULL,
    INDEX idx_activite   (activite_principale)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
