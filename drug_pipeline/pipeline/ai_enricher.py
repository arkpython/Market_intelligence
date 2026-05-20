"""
Market Intelligence Pipeline — AI Enricher
Uses Anthropic API + web search to pull real-time market intelligence
for each oncology disease state.
"""

import os
import json
import time
import logging
from datetime import datetime, timezone

import anthropic

from .config import AI_MODEL, DISEASE_STATES, MARKET_SIZE_BASELINE, ALL_DISEASE_STATES

logger = logging.getLogger(__name__)


def _get_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set.")
    return anthropic.Anthropic(api_key=api_key)


def _therapeutic_area(disease_state):
    for area, states in DISEASE_STATES.items():
        if disease_state in states:
            return area
    return "Other"


ENRICHMENT_PROMPT = """
You are a senior oncology market intelligence analyst. Provide a comprehensive, up-to-date
market intelligence report for the following disease state.

Disease State: {disease_state}
Therapeutic Area: {therapeutic_area}

Search the web for the LATEST information (2024-2025) and return a JSON object with EXACTLY this structure:

{{
  "key_drugs": [
    {{
      "name": "drug name (INN)",
      "brand_name": "brand name if approved, else null",
      "company": "pharmaceutical company",
      "stage": "Approved | Phase 3 | Phase 2 | Phase 1",
      "moa": "mechanism of action",
      "drug_class": "ADC | PARP inhibitor | BTK inhibitor | CAR-T | Bispecific | IO/PD-1 | IO/PD-L1 | ARPI | VEGFR | CDK4/6 | JAK inhibitor | FGFR | RET | ALK | KRAS | HER2 | Other",
      "targets": ["target1"],
      "primary_endpoint": "e.g. rPFS, OS, ORR, EFS, DFS, PFS",
      "key_trial": "trial name",
      "nct_id": "NCT number",
      "indication": "specific indication",
      "approval_year": null
    }}
  ],
  "recent_approvals": [{{
    "drug_name": "", "brand_name": "", "company": "",
    "approval_date": "YYYY-MM", "indication": "", "endpoint_basis": ""
  }}],
  "late_stage_pipeline": [{{
    "drug_name": "", "company": "", "phase": "Phase 3",
    "indication": "", "primary_endpoint": "", "readout_expected": "", "nct_id": ""
  }}],
  "key_companies": [],
  "notable_endpoints": [{{
    "endpoint": "", "context": ""
  }}],
  "competitive_dynamics": "2-3 sentences",
  "unmet_needs": "2-3 sentences",
  "growth_drivers": "2-3 sentences",
  "market_size_usd_bn": {market_size_baseline},
  "cagr_pct": {cagr_baseline},
  "patients_us": {patients_us_baseline},
  "reference_links": [{{
    "title": "", "url": "https://...",
    "type": "FDA label | ClinicalTrials | Press release | Peer-reviewed | Market report | News"
  }}],
  "ai_summary": "3-4 sentence executive summary"
}}

Include 8-15 drugs in key_drugs, at least 5 reference links. Return ONLY the JSON.
"""


def enrich_disease_state(disease_state: str) -> dict:
    """AI-enrich one disease state. Returns market_intelligence dict."""
    client   = _get_client()
    baseline = MARKET_SIZE_BASELINE.get(disease_state, {})
    ta       = _therapeutic_area(disease_state)

    prompt = ENRICHMENT_PROMPT.format(
        disease_state=disease_state, therapeutic_area=ta,
        market_size_baseline=baseline.get("size_usd_bn", "null"),
        cagr_baseline=baseline.get("cagr_pct", "null"),
        patients_us_baseline=baseline.get("patients_us", "null"),
    )
    logger.info(f"  AI enriching → {disease_state}")

    try:
        response = client.messages.create(
            model=AI_MODEL, max_tokens=4096,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = ""
        for block in response.content:
            if block.type == "text":
                raw_text = block.text
        clean = raw_text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip().rstrip("```").strip()
        parsed = json.loads(clean)
        return {
            "disease_state":       disease_state,
            "therapeutic_area":    ta,
            "market_size_usd_bn":  parsed.get("market_size_usd_bn", baseline.get("size_usd_bn")),
            "cagr_pct":            parsed.get("cagr_pct", baseline.get("cagr_pct")),
            "patients_us":         parsed.get("patients_us", baseline.get("patients_us")),
            "key_drugs":           parsed.get("key_drugs", []),
            "recent_approvals":    parsed.get("recent_approvals", []),
            "late_stage_pipeline": parsed.get("late_stage_pipeline", []),
            "key_companies":       parsed.get("key_companies", []),
            "notable_endpoints":   parsed.get("notable_endpoints", []),
            "competitive_dynamics":parsed.get("competitive_dynamics", ""),
            "unmet_needs":         parsed.get("unmet_needs", ""),
            "growth_drivers":      parsed.get("growth_drivers", ""),
            "reference_links":     parsed.get("reference_links", []),
            "ai_summary":          parsed.get("ai_summary", ""),
            "last_enriched":       datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"    AI enrichment failed for {disease_state}: {e}")
        return {
            "disease_state": disease_state, "therapeutic_area": ta,
            "market_size_usd_bn": baseline.get("size_usd_bn"),
            "cagr_pct": baseline.get("cagr_pct"), "patients_us": baseline.get("patients_us"),
            "key_drugs": [], "recent_approvals": [], "late_stage_pipeline": [],
            "key_companies": [], "notable_endpoints": [],
            "competitive_dynamics": "", "unmet_needs": "", "growth_drivers": "",
            "reference_links": [],
            "ai_summary": f"AI enrichment unavailable for {disease_state}. Baseline data shown.",
            "last_enriched": datetime.now(timezone.utc).isoformat(),
        }


def enrich_all_disease_states(disease_states=None):
    """Enrich all or subset of disease states."""
    targets = disease_states or ALL_DISEASE_STATES
    results = {}
    for i, ds in enumerate(targets):
        results[ds] = enrich_disease_state(ds)
        if i < len(targets) - 1:
            time.sleep(2)
    return results


def build_pipeline_drugs_from_mi(mi_data: dict) -> list[dict]:
    """Convert AI-enriched market intelligence into drug_pipeline records."""
    records = []
    for disease_state, mi in mi_data.items():
        ta = mi.get("therapeutic_area", "")
        for drug in mi.get("key_drugs", []):
            nct = drug.get("nct_id", "")
            ref_links = []
            if nct and nct.startswith("NCT"):
                ref_links.append({"title": f"ClinicalTrials.gov — {drug.get('key_trial', nct)}",
                                   "url": f"https://clinicaltrials.gov/study/{nct}"})
            records.append({
                "drug_name":           drug.get("name", ""),
                "brand_name":          drug.get("brand_name"),
                "inn_name":            drug.get("name", ""),
                "company":             drug.get("company", ""),
                "disease_state":       disease_state,
                "therapeutic_area":    ta,
                "pipeline_stage":      drug.get("stage", "Phase 2"),
                "mechanism_of_action": drug.get("moa", ""),
                "drug_class":          drug.get("drug_class", ""),
                "targets":             drug.get("targets", []),
                "primary_endpoint":    drug.get("primary_endpoint", ""),
                "key_endpoints":       [drug.get("primary_endpoint")] if drug.get("primary_endpoint") else [],
                "trial_nct_ids":       [nct] if nct else [],
                "approval_date":       str(drug.get("approval_year", "")) if drug.get("approval_year") else "",
                "fda_application":     "",
                "market_size_usd_bn":  mi.get("market_size_usd_bn"),
                "cagr_pct":            mi.get("cagr_pct"),
                "reference_links":     ref_links + mi.get("reference_links", [])[:3],
                "notes":               drug.get("indication", ""),
            })
    return [r for r in records if r["drug_name"]]
