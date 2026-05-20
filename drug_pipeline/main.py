#!/usr/bin/env python3
"""
Market Intelligence Pipeline - Main Entry Point
Orchestrates the full data fetch -> enrichment -> store -> report cycle.

Usage:
  python main.py                     # Full pipeline
  python main.py --ai-only           # AI enrichment + pipeline rebuild only
  python main.py --trials-only       # ClinicalTrials.gov fetch only
  python main.py --report-only       # Regenerate reports from existing DB
  python main.py --disease "Prostate Cancer"  # Single disease state
  python main.py --summary           # Print pipeline summary table
"""

import argparse
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(__file__).parent / "data" / "pipeline.log", mode="a"),
    ],
)
logger = logging.getLogger("main")

from pipeline.config import ALL_DISEASE_STATES, DISEASE_STATES
from pipeline.database import (
    initialize_db, get_connection, DB_PATH,
    upsert_trial, upsert_approved_drug, upsert_market_intelligence,
    upsert_pipeline_drug, log_run_start, log_run_end, get_full_pipeline_summary,
)
from pipeline.clinicaltrials import fetch_trials_for_disease
from pipeline.fda import fetch_approved_drugs_for_disease
from pipeline.ai_enricher import enrich_disease_state, build_pipeline_drugs_from_mi
from pipeline.report import generate_markdown_report, generate_html_report


def step_fetch_trials(disease_states):
    logger.info("== STEP 1: ClinicalTrials.gov Fetch ==")
    total = 0
    with get_connection() as conn:
        for ds in disease_states:
            trials = list(fetch_trials_for_disease(ds))
            for trial in trials:
                upsert_trial(conn, trial)
            conn.commit()
            total += len(trials)
            logger.info(f"  [OK] {ds}: {len(trials)} trials stored")
    logger.info(f"  Total trials stored: {total}")
    return total


def step_fetch_fda(disease_states):
    logger.info("== STEP 2: OpenFDA Approved Drugs ==")
    total = 0
    with get_connection() as conn:
        for ds in disease_states:
            drugs = fetch_approved_drugs_for_disease(ds)
            for drug in drugs:
                upsert_approved_drug(conn, drug)
            conn.commit()
            total += len(drugs)
            logger.info(f"  [OK] {ds}: {len(drugs)} approved drugs stored")
    logger.info(f"  Total approved drugs stored: {total}")
    return total


def step_ai_enrich(disease_states):
    logger.info("== STEP 3: AI Market Intelligence Enrichment ==")
    mi_data = {}
    with get_connection() as conn:
        for ds in disease_states:
            mi = enrich_disease_state(ds)
            upsert_market_intelligence(conn, mi)
            mi_data[ds] = mi
            conn.commit()
            logger.info(f"  [OK] {ds}: enriched ({len(mi.get('key_drugs', []))} drugs identified)")
    logger.info(f"  Total disease states enriched: {len(mi_data)}")
    return len(mi_data), mi_data


def step_build_pipeline(mi_data):
    logger.info("== STEP 4: Building Drug Pipeline Table ==")
    pipeline_drugs = build_pipeline_drugs_from_mi(mi_data)
    with get_connection() as conn:
        for drug in pipeline_drugs:
            upsert_pipeline_drug(conn, drug)
        conn.commit()
    logger.info(f"  Drug pipeline records upserted: {len(pipeline_drugs)}")
    return len(pipeline_drugs)


def step_generate_reports():
    logger.info("== STEP 5: Generating Reports ==")
    md_path   = generate_markdown_report()
    html_path = generate_html_report()
    logger.info(f"  Markdown: {md_path}")
    logger.info(f"  HTML:     {html_path}")


def print_summary():
    with get_connection() as conn:
        rows = get_full_pipeline_summary(conn)
    if not rows:
        print("No data in database. Run the pipeline first.")
        return
    print("\n" + "=" * 95)
    print(f"{'ONCOLOGY PIPELINE SUMMARY':^95}")
    print("=" * 95)
    print(f"{'Disease State':<30} {'Area':<22} {'Appr':>5} {'Ph3':>5} {'Ph2':>5} {'Market $B':>10} {'CAGR':>6}")
    print("-" * 95)
    for r in rows:
        print(
            f"{r['disease_state']:<30} {(r['therapeutic_area'] or ''):<22} "
            f"{(r['approved'] or 0):>5} {(r['phase3'] or 0):>5} {(r['phase2'] or 0):>5} "
            f"{'$' + str(r['market_size_usd_bn']) + 'B' if r['market_size_usd_bn'] else '--':>10} "
            f"{str(r['cagr_pct']) + '%' if r['cagr_pct'] else '--':>6}"
        )
    print("=" * 95 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Oncology Market Intelligence Pipeline")
    parser.add_argument("--ai-only",     action="store_true", help="Run AI enrichment only")
    parser.add_argument("--trials-only", action="store_true", help="Fetch ClinicalTrials.gov only")
    parser.add_argument("--report-only", action="store_true", help="Regenerate reports from DB")
    parser.add_argument("--disease",     type=str,            help="Single disease state to process")
    parser.add_argument("--summary",     action="store_true", help="Print pipeline summary table")
    parser.add_argument("--no-report",   action="store_true", help="Skip report generation")
    args = parser.parse_args()

    # Ensure data dir exists
    (Path(__file__).parent / "data").mkdir(exist_ok=True)
    initialize_db()

    if args.summary:
        print_summary()
        return

    if args.report_only:
        step_generate_reports()
        return

    if args.disease:
        if args.disease not in ALL_DISEASE_STATES:
            logger.error(f"Unknown disease state: '{args.disease}'. Valid: {ALL_DISEASE_STATES}")
            sys.exit(1)
        disease_states = [args.disease]
    else:
        disease_states = ALL_DISEASE_STATES

    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    counts = {"trials": 0, "drugs": 0, "diseases": 0, "pipeline": 0}

    with get_connection() as conn:
        log_run_start(conn, run_id)

    logger.info(f"\n{'='*60}")
    logger.info(f"  ONCOLOGY PIPELINE - RUN {run_id}")
    logger.info(f"  Disease States: {len(disease_states)}")
    logger.info(f"  Mode: {'AI Only' if args.ai_only else 'Trials Only' if args.trials_only else 'Full Pipeline'}")
    logger.info(f"{'='*60}\n")

    try:
        if not args.ai_only and not args.trials_only:
            counts["trials"] = step_fetch_trials(disease_states)
            counts["drugs"]   = step_fetch_fda(disease_states)
            n_enriched, mi_data = step_ai_enrich(disease_states)
            counts["diseases"] = n_enriched
            counts["pipeline"] = step_build_pipeline(mi_data)
        elif args.ai_only:
            n_enriched, mi_data = step_ai_enrich(disease_states)
            counts["diseases"] = n_enriched
            counts["pipeline"] = step_build_pipeline(mi_data)
        elif args.trials_only:
            counts["trials"] = step_fetch_trials(disease_states)

        if not args.no_report:
            step_generate_reports()

        with get_connection() as conn:
            log_run_end(conn, run_id, counts, status="success")

        logger.info("\n[SUCCESS] Pipeline completed!")
        print_summary()

    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user.")
        with get_connection() as conn:
            log_run_end(conn, run_id, counts, status="failed", error="KeyboardInterrupt")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        with get_connection() as conn:
            log_run_end(conn, run_id, counts, status="failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
