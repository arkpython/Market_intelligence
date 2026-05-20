"""
Market Intelligence Pipeline — Database Layer
SQLite schema, CRUD operations, and query helpers.
"""

import sqlite3
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "oncology_pipeline.db"

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS trials (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    nct_id              TEXT    UNIQUE NOT NULL,
    title               TEXT,
    brief_title         TEXT,
    phase               TEXT,
    status              TEXT,
    sponsor             TEXT,
    lead_sponsor_class  TEXT,
    start_date          TEXT,
    primary_completion  TEXT,
    study_completion    TEXT,
    enrollment          INTEGER,
    conditions          TEXT,
    disease_state       TEXT,
    therapeutic_area    TEXT,
    interventions       TEXT,
    drug_names          TEXT,
    primary_endpoint    TEXT,
    secondary_endpoints TEXT,
    outcome_measures    TEXT,
    locations           TEXT,
    results_available   INTEGER DEFAULT 0,
    study_url           TEXT,
    last_updated        TEXT,
    fetched_at          TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS approved_drugs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_name           TEXT,
    brand_name          TEXT,
    company             TEXT,
    application_number  TEXT    UNIQUE,
    approval_date       TEXT,
    indication          TEXT,
    disease_state       TEXT,
    therapeutic_area    TEXT,
    drug_type           TEXT,
    reference_link      TEXT,
    fetched_at          TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS market_intelligence (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    disease_state       TEXT    UNIQUE NOT NULL,
    therapeutic_area    TEXT,
    market_size_usd_bn  REAL,
    cagr_pct            REAL,
    patients_us         INTEGER,
    key_drugs           TEXT,
    recent_approvals    TEXT,
    late_stage_pipeline TEXT,
    key_companies       TEXT,
    notable_endpoints   TEXT,
    competitive_dynamics TEXT,
    unmet_needs         TEXT,
    growth_drivers      TEXT,
    reference_links     TEXT,
    ai_summary          TEXT,
    last_enriched       TEXT,
    fetched_at          TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS drug_pipeline (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_name           TEXT    NOT NULL,
    brand_name          TEXT,
    inn_name            TEXT,
    company             TEXT,
    disease_state       TEXT,
    therapeutic_area    TEXT,
    pipeline_stage      TEXT,
    mechanism_of_action TEXT,
    drug_class          TEXT,
    targets             TEXT,
    primary_endpoint    TEXT,
    key_endpoints       TEXT,
    trial_nct_ids       TEXT,
    approval_date       TEXT,
    fda_application     TEXT,
    market_size_usd_bn  REAL,
    cagr_pct            REAL,
    reference_links     TEXT,
    notes               TEXT,
    last_updated        TEXT    DEFAULT (datetime('now')),
    UNIQUE(drug_name, disease_state, pipeline_stage)
);

CREATE TABLE IF NOT EXISTS refresh_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id              TEXT    UNIQUE,
    started_at          TEXT,
    completed_at        TEXT,
    status              TEXT,
    trials_fetched      INTEGER DEFAULT 0,
    drugs_fetched       INTEGER DEFAULT 0,
    diseases_enriched   INTEGER DEFAULT 0,
    pipeline_records    INTEGER DEFAULT 0,
    error_message       TEXT,
    notes               TEXT
);

CREATE INDEX IF NOT EXISTS idx_trials_disease   ON trials(disease_state);
CREATE INDEX IF NOT EXISTS idx_trials_phase     ON trials(phase);
CREATE INDEX IF NOT EXISTS idx_pipeline_disease ON drug_pipeline(disease_state);
CREATE INDEX IF NOT EXISTS idx_pipeline_stage   ON drug_pipeline(pipeline_stage);
CREATE INDEX IF NOT EXISTS idx_pipeline_company ON drug_pipeline(company);
CREATE INDEX IF NOT EXISTS idx_mi_disease       ON market_intelligence(disease_state);
"""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialize_db(db_path: Path = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
    logger.info(f"Database initialized at {db_path}")


def _j(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, str):
        return val
    return json.dumps(val, ensure_ascii=False)


def upsert_trial(conn, trial):
    conn.execute("""
        INSERT INTO trials (
            nct_id, title, brief_title, phase, status, sponsor,
            lead_sponsor_class, start_date, primary_completion, study_completion,
            enrollment, conditions, disease_state, therapeutic_area,
            interventions, drug_names, primary_endpoint, secondary_endpoints,
            outcome_measures, locations, results_available, study_url, last_updated
        ) VALUES (
            :nct_id, :title, :brief_title, :phase, :status, :sponsor,
            :lead_sponsor_class, :start_date, :primary_completion, :study_completion,
            :enrollment, :conditions, :disease_state, :therapeutic_area,
            :interventions, :drug_names, :primary_endpoint, :secondary_endpoints,
            :outcome_measures, :locations, :results_available, :study_url, :last_updated
        )
        ON CONFLICT(nct_id) DO UPDATE SET
            phase=excluded.phase, status=excluded.status,
            enrollment=excluded.enrollment, drug_names=excluded.drug_names,
            primary_endpoint=excluded.primary_endpoint, fetched_at=datetime('now')
    """, {
        "nct_id": trial.get("nct_id"), "title": trial.get("title"),
        "brief_title": trial.get("brief_title"), "phase": trial.get("phase"),
        "status": trial.get("status"), "sponsor": trial.get("sponsor"),
        "lead_sponsor_class": trial.get("lead_sponsor_class"),
        "start_date": trial.get("start_date"), "primary_completion": trial.get("primary_completion"),
        "study_completion": trial.get("study_completion"), "enrollment": trial.get("enrollment"),
        "conditions": _j(trial.get("conditions")), "disease_state": trial.get("disease_state"),
        "therapeutic_area": trial.get("therapeutic_area"), "interventions": _j(trial.get("interventions")),
        "drug_names": _j(trial.get("drug_names")), "primary_endpoint": trial.get("primary_endpoint"),
        "secondary_endpoints": _j(trial.get("secondary_endpoints")),
        "outcome_measures": _j(trial.get("outcome_measures")), "locations": _j(trial.get("locations")),
        "results_available": int(bool(trial.get("results_available"))),
        "study_url": trial.get("study_url"), "last_updated": trial.get("last_updated"),
    })


def upsert_approved_drug(conn, drug):
    conn.execute("""
        INSERT INTO approved_drugs (
            drug_name, brand_name, company, application_number,
            approval_date, indication, disease_state, therapeutic_area, drug_type, reference_link
        ) VALUES (
            :drug_name, :brand_name, :company, :application_number,
            :approval_date, :indication, :disease_state, :therapeutic_area, :drug_type, :reference_link
        )
        ON CONFLICT(application_number) DO UPDATE SET
            drug_name=excluded.drug_name, company=excluded.company, fetched_at=datetime('now')
    """, drug)


def upsert_market_intelligence(conn, mi):
    conn.execute("""
        INSERT INTO market_intelligence (
            disease_state, therapeutic_area, market_size_usd_bn, cagr_pct, patients_us,
            key_drugs, recent_approvals, late_stage_pipeline, key_companies, notable_endpoints,
            competitive_dynamics, unmet_needs, growth_drivers, reference_links, ai_summary, last_enriched
        ) VALUES (
            :disease_state, :therapeutic_area, :market_size_usd_bn, :cagr_pct, :patients_us,
            :key_drugs, :recent_approvals, :late_stage_pipeline, :key_companies, :notable_endpoints,
            :competitive_dynamics, :unmet_needs, :growth_drivers, :reference_links, :ai_summary, :last_enriched
        )
        ON CONFLICT(disease_state) DO UPDATE SET
            market_size_usd_bn=excluded.market_size_usd_bn, cagr_pct=excluded.cagr_pct,
            patients_us=excluded.patients_us, key_drugs=excluded.key_drugs,
            recent_approvals=excluded.recent_approvals, late_stage_pipeline=excluded.late_stage_pipeline,
            key_companies=excluded.key_companies, notable_endpoints=excluded.notable_endpoints,
            competitive_dynamics=excluded.competitive_dynamics, unmet_needs=excluded.unmet_needs,
            growth_drivers=excluded.growth_drivers, reference_links=excluded.reference_links,
            ai_summary=excluded.ai_summary, last_enriched=excluded.last_enriched, fetched_at=datetime('now')
    """, {
        "disease_state": mi.get("disease_state"), "therapeutic_area": mi.get("therapeutic_area"),
        "market_size_usd_bn": mi.get("market_size_usd_bn"), "cagr_pct": mi.get("cagr_pct"),
        "patients_us": mi.get("patients_us"), "key_drugs": _j(mi.get("key_drugs")),
        "recent_approvals": _j(mi.get("recent_approvals")), "late_stage_pipeline": _j(mi.get("late_stage_pipeline")),
        "key_companies": _j(mi.get("key_companies")), "notable_endpoints": _j(mi.get("notable_endpoints")),
        "competitive_dynamics": mi.get("competitive_dynamics"), "unmet_needs": mi.get("unmet_needs"),
        "growth_drivers": mi.get("growth_drivers"), "reference_links": _j(mi.get("reference_links")),
        "ai_summary": mi.get("ai_summary"), "last_enriched": mi.get("last_enriched"),
    })


def upsert_pipeline_drug(conn, drug):
    conn.execute("""
        INSERT INTO drug_pipeline (
            drug_name, brand_name, inn_name, company, disease_state, therapeutic_area,
            pipeline_stage, mechanism_of_action, drug_class, targets, primary_endpoint,
            key_endpoints, trial_nct_ids, approval_date, fda_application,
            market_size_usd_bn, cagr_pct, reference_links, notes
        ) VALUES (
            :drug_name, :brand_name, :inn_name, :company, :disease_state, :therapeutic_area,
            :pipeline_stage, :mechanism_of_action, :drug_class, :targets, :primary_endpoint,
            :key_endpoints, :trial_nct_ids, :approval_date, :fda_application,
            :market_size_usd_bn, :cagr_pct, :reference_links, :notes
        )
        ON CONFLICT(drug_name, disease_state, pipeline_stage) DO UPDATE SET
            company=excluded.company, mechanism_of_action=excluded.mechanism_of_action,
            drug_class=excluded.drug_class, primary_endpoint=excluded.primary_endpoint,
            reference_links=excluded.reference_links, last_updated=datetime('now')
    """, {
        "drug_name": drug.get("drug_name"), "brand_name": drug.get("brand_name"),
        "inn_name": drug.get("inn_name"), "company": drug.get("company"),
        "disease_state": drug.get("disease_state"), "therapeutic_area": drug.get("therapeutic_area"),
        "pipeline_stage": drug.get("pipeline_stage"), "mechanism_of_action": drug.get("mechanism_of_action"),
        "drug_class": drug.get("drug_class"), "targets": _j(drug.get("targets")),
        "primary_endpoint": drug.get("primary_endpoint"), "key_endpoints": _j(drug.get("key_endpoints")),
        "trial_nct_ids": _j(drug.get("trial_nct_ids")), "approval_date": drug.get("approval_date"),
        "fda_application": drug.get("fda_application"), "market_size_usd_bn": drug.get("market_size_usd_bn"),
        "cagr_pct": drug.get("cagr_pct"), "reference_links": _j(drug.get("reference_links")),
        "notes": drug.get("notes"),
    })


def get_pipeline_by_disease(conn, disease_state):
    cur = conn.execute(
        "SELECT * FROM drug_pipeline WHERE disease_state=? ORDER BY pipeline_stage, company",
        (disease_state,)
    )
    return [dict(r) for r in cur.fetchall()]


def get_pipeline_by_company(conn, company):
    cur = conn.execute(
        "SELECT * FROM drug_pipeline WHERE company LIKE ? ORDER BY disease_state, pipeline_stage",
        (f"%{company}%",)
    )
    return [dict(r) for r in cur.fetchall()]


def get_market_intelligence(conn, disease_state):
    cur = conn.execute("SELECT * FROM market_intelligence WHERE disease_state=?", (disease_state,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_full_pipeline_summary(conn):
    cur = conn.execute("""
        SELECT dp.disease_state, dp.therapeutic_area,
               COUNT(DISTINCT dp.drug_name) AS total_drugs,
               SUM(CASE WHEN dp.pipeline_stage='Approved' THEN 1 ELSE 0 END) AS approved,
               SUM(CASE WHEN dp.pipeline_stage='Phase 3'  THEN 1 ELSE 0 END) AS phase3,
               SUM(CASE WHEN dp.pipeline_stage='Phase 2'  THEN 1 ELSE 0 END) AS phase2,
               mi.market_size_usd_bn, mi.cagr_pct, mi.patients_us
        FROM drug_pipeline dp
        LEFT JOIN market_intelligence mi USING (disease_state)
        GROUP BY dp.disease_state
        ORDER BY mi.market_size_usd_bn DESC
    """)
    return [dict(r) for r in cur.fetchall()]


def log_run_start(conn, run_id):
    conn.execute(
        "INSERT INTO refresh_log (run_id, started_at, status) VALUES (?,datetime('now'),'running') ON CONFLICT(run_id) DO NOTHING",
        (run_id,)
    )
    conn.commit()


def log_run_end(conn, run_id, counts, status="success", error=None):
    conn.execute("""
        UPDATE refresh_log SET completed_at=datetime('now'), status=?,
            trials_fetched=?, drugs_fetched=?, diseases_enriched=?, pipeline_records=?, error_message=?
        WHERE run_id=?
    """, (status, counts.get("trials",0), counts.get("drugs",0),
           counts.get("diseases",0), counts.get("pipeline",0), error, run_id))
    conn.commit()
