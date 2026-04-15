#!/usr/bin/env python3
"""
SQLite database layer for Structural Inflection Radar v3.
Manages all DB operations: init, CRUD, queries.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "radar.db"

SCHEMA_SQL = """
-- Domain management
CREATE TABLE IF NOT EXISTS domains (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    slug          TEXT    NOT NULL UNIQUE,
    name_ja       TEXT    NOT NULL,
    name_en       TEXT    NOT NULL,
    description   TEXT    DEFAULT '',
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    updated_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
);

-- Domain keywords (replaces hardcoded ENERGY_KEYWORDS / HN_KEYWORDS)
CREATE TABLE IF NOT EXISTS domain_keywords (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id     INTEGER NOT NULL REFERENCES domains(id),
    keyword       TEXT    NOT NULL,
    source_type   TEXT    NOT NULL DEFAULT 'all',
    is_active     INTEGER NOT NULL DEFAULT 1,
    UNIQUE(domain_id, keyword, source_type)
);
CREATE INDEX IF NOT EXISTS idx_domain_keywords_domain ON domain_keywords(domain_id);

-- Data sources
CREATE TABLE IF NOT EXISTS sources (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    slug          TEXT    NOT NULL UNIQUE,
    name          TEXT    NOT NULL,
    source_type   TEXT    NOT NULL,
    base_url      TEXT    NOT NULL,
    credibility_weight REAL NOT NULL DEFAULT 0.5,
    is_active     INTEGER NOT NULL DEFAULT 1
);

-- Raw collected items
CREATE TABLE IF NOT EXISTS raw_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id   TEXT    NOT NULL,
    domain_id     INTEGER NOT NULL REFERENCES domains(id),
    source_id     INTEGER NOT NULL REFERENCES sources(id),
    title         TEXT    NOT NULL DEFAULT '',
    abstract      TEXT    DEFAULT '',
    url           TEXT    DEFAULT '',
    publication_date TEXT,
    cited_by_count INTEGER DEFAULT 0,
    query_keyword TEXT,
    collected_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    run_id        INTEGER REFERENCES pipeline_runs(id),
    UNIQUE(external_id, domain_id)
);
CREATE INDEX IF NOT EXISTS idx_raw_items_domain ON raw_items(domain_id);
CREATE INDEX IF NOT EXISTS idx_raw_items_source ON raw_items(source_id);
CREATE INDEX IF NOT EXISTS idx_raw_items_run ON raw_items(run_id);

-- Scored items (1:1 with raw_items)
CREATE TABLE IF NOT EXISTS scored_items (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_item_id      INTEGER NOT NULL REFERENCES raw_items(id),
    model            TEXT    NOT NULL,
    credibility_weight REAL  NOT NULL,
    threshold_proximity_signal   INTEGER NOT NULL DEFAULT 0,
    threshold_proximity_evidence TEXT    DEFAULT '',
    external_pressure_signal     INTEGER NOT NULL DEFAULT 0,
    external_pressure_evidence   TEXT    DEFAULT '',
    tech_cycle_position_signal   INTEGER NOT NULL DEFAULT 0,
    tech_cycle_position_evidence TEXT    DEFAULT '',
    institutional_change_signal  INTEGER NOT NULL DEFAULT 0,
    institutional_change_evidence TEXT   DEFAULT '',
    uncertainty_resolution_signal INTEGER NOT NULL DEFAULT 0,
    uncertainty_resolution_evidence TEXT DEFAULT '',
    error            TEXT    DEFAULT NULL,
    scored_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    run_id           INTEGER REFERENCES pipeline_runs(id),
    UNIQUE(raw_item_id)
);
CREATE INDEX IF NOT EXISTS idx_scored_items_raw ON scored_items(raw_item_id);
CREATE INDEX IF NOT EXISTS idx_scored_items_run ON scored_items(run_id);

-- Theme tags from scoring
CREATE TABLE IF NOT EXISTS scored_item_tags (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scored_item_id  INTEGER NOT NULL REFERENCES scored_items(id),
    tag             TEXT    NOT NULL,
    UNIQUE(scored_item_id, tag)
);
CREATE INDEX IF NOT EXISTS idx_scored_item_tags_tag ON scored_item_tags(tag);

-- Theme master
CREATE TABLE IF NOT EXISTS themes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id     INTEGER NOT NULL REFERENCES domains(id),
    tag           TEXT    NOT NULL,
    name_ja       TEXT    DEFAULT NULL,
    first_seen_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    UNIQUE(domain_id, tag)
);
CREATE INDEX IF NOT EXISTS idx_themes_domain ON themes(domain_id);

-- Theme scores (time series)
CREATE TABLE IF NOT EXISTS theme_scores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    theme_id        INTEGER NOT NULL REFERENCES themes(id),
    run_id          INTEGER NOT NULL REFERENCES pipeline_runs(id),
    scan_date       TEXT    NOT NULL,
    item_count      INTEGER NOT NULL DEFAULT 0,
    composite_score REAL    NOT NULL DEFAULT 0,
    composite_delta REAL    DEFAULT NULL,
    UNIQUE(theme_id, scan_date)
);
CREATE INDEX IF NOT EXISTS idx_theme_scores_theme ON theme_scores(theme_id);
CREATE INDEX IF NOT EXISTS idx_theme_scores_date ON theme_scores(scan_date);

-- Theme x axis scores (time series)
CREATE TABLE IF NOT EXISTS theme_axes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    theme_score_id  INTEGER NOT NULL REFERENCES theme_scores(id),
    axis            TEXT    NOT NULL,
    score           REAL    NOT NULL DEFAULT 0,
    signal_count    INTEGER NOT NULL DEFAULT 0,
    delta           REAL    DEFAULT NULL,
    UNIQUE(theme_score_id, axis)
);
CREATE INDEX IF NOT EXISTS idx_theme_axes_score ON theme_axes(theme_score_id);

-- Theme evidence per axis
CREATE TABLE IF NOT EXISTS theme_evidence (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    theme_score_id  INTEGER NOT NULL REFERENCES theme_scores(id),
    axis            TEXT    NOT NULL,
    evidence_text   TEXT    NOT NULL,
    source_item_id  INTEGER REFERENCES raw_items(id)
);
CREATE INDEX IF NOT EXISTS idx_theme_evidence_score ON theme_evidence(theme_score_id);

-- Pipeline execution history
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id       INTEGER NOT NULL REFERENCES domains(id),
    started_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
    completed_at    TEXT    DEFAULT NULL,
    status          TEXT    NOT NULL DEFAULT 'running',
    collect_count   INTEGER DEFAULT NULL,
    score_count     INTEGER DEFAULT NULL,
    score_error_count INTEGER DEFAULT NULL,
    theme_count     INTEGER DEFAULT NULL,
    days_back       INTEGER DEFAULT 30,
    model           TEXT    DEFAULT NULL,
    error_message   TEXT    DEFAULT NULL,
    api_calls       INTEGER DEFAULT 0,
    estimated_cost_usd REAL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_domain ON pipeline_runs(domain_id);
"""


def get_connection() -> sqlite3.Connection:
    """Get a connection to the radar database with WAL mode."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize all tables."""
    conn = get_connection()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


def seed_data():
    """Insert initial domains and sources."""
    conn = get_connection()
    cur = conn.cursor()

    # Sources
    sources = [
        ("openalex", "OpenAlex", "academic", "https://api.openalex.org/works", 1.0),
        ("hackernews", "HackerNews", "tech_media", "https://hn.algolia.com/api/v1/search", 0.7),
        ("arxiv", "arXiv", "academic", "http://export.arxiv.org/api/query", 0.8),
    ]
    for slug, name, stype, url, weight in sources:
        cur.execute(
            "INSERT OR IGNORE INTO sources (slug, name, source_type, base_url, credibility_weight) VALUES (?, ?, ?, ?, ?)",
            (slug, name, stype, url, weight),
        )

    # Load domain configs from YAML files
    import yaml
    domains_dir = Path(__file__).parent.parent / "domains"
    for yaml_file in sorted(domains_dir.glob("*.yaml")):
        with open(yaml_file, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        cur.execute(
            "INSERT OR IGNORE INTO domains (slug, name_ja, name_en, description) VALUES (?, ?, ?, ?)",
            (cfg["domain_id"], cfg["domain_name_ja"], cfg["domain_name_en"], cfg.get("description", "")),
        )
        domain_id = cur.execute("SELECT id FROM domains WHERE slug = ?", (cfg["domain_id"],)).fetchone()["id"]

        # Insert keywords per source
        for source_key, source_cfg in cfg.get("sources", {}).items():
            for kw in source_cfg.get("keywords", []):
                cur.execute(
                    "INSERT OR IGNORE INTO domain_keywords (domain_id, keyword, source_type) VALUES (?, ?, ?)",
                    (domain_id, kw, source_key),
                )

    conn.commit()
    conn.close()
    print("Seed data inserted")


def get_keywords(domain_slug: str, source_type: str = "all") -> list[str]:
    """Get active keywords for a domain and source type."""
    conn = get_connection()
    if source_type == "all":
        rows = conn.execute(
            "SELECT DISTINCT keyword FROM domain_keywords dk JOIN domains d ON dk.domain_id = d.id WHERE d.slug = ? AND dk.is_active = 1",
            (domain_slug,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT DISTINCT keyword FROM domain_keywords dk JOIN domains d ON dk.domain_id = d.id WHERE d.slug = ? AND dk.source_type IN (?, 'all') AND dk.is_active = 1",
            (domain_slug, source_type),
        ).fetchall()
    conn.close()
    return [r["keyword"] for r in rows]


def get_active_domains() -> list[dict]:
    """Get all active domains."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM domains WHERE is_active = 1 ORDER BY slug").fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    seed_data()
