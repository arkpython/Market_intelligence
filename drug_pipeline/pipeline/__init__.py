"""
Oncology Market Intelligence Pipeline
Fetches, enriches, and stores drug pipeline data for oncology disease states.
"""

from .config import ALL_DISEASE_STATES, DISEASE_STATES
from .database import initialize_db, get_connection
from .clinicaltrials import fetch_all_oncology_trials
from .fda import fetch_all_approved_drugs
from .ai_enricher import enrich_all_disease_states, build_pipeline_drugs_from_mi
from .report import generate_markdown_report, generate_html_report

__all__ = [
    "ALL_DISEASE_STATES",
    "DISEASE_STATES",
    "initialize_db",
    "get_connection",
    "fetch_all_oncology_trials",
    "fetch_all_approved_drugs",
    "enrich_all_disease_states",
    "build_pipeline_drugs_from_mi",
    "generate_markdown_report",
    "generate_html_report",
]
