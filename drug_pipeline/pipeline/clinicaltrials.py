"""
Market Intelligence Pipeline — ClinicalTrials.gov Fetcher
Pulls Phase 2/3 oncology trials from the ClinicalTrials.gov v2 API.
"""

import time
import logging
import requests
from typing import Generator

from .config import (
    CLINICALTRIALS_BASE_URL, CONDITION_SEARCH_TERMS,
    DISEASE_STATES, PHASE_MAPPING, STATUS_MAPPING, MAX_TRIALS_PER_DISEASE,
)

logger = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json", "User-Agent": "OncologyPipelineTracker/1.0"})


def _therapeutic_area(disease_state):
    for area, states in DISEASE_STATES.items():
        if disease_state in states:
            return area
    return "Other"


def _map_phase(raw_phases):
    if not raw_phases:
        return "N/A"
    return PHASE_MAPPING.get(raw_phases[0], raw_phases[0])


def _map_status(raw_status):
    return STATUS_MAPPING.get(raw_status, raw_status.replace("_", " ").title() if raw_status else "Unknown")


def _extract_drug_names(interventions):
    drugs = []
    for inv in interventions or []:
        if inv.get("type") in ("DRUG", "BIOLOGICAL", "COMBINATION_PRODUCT"):
            name = inv.get("name", "").strip()
            if name and len(name) > 1:
                drugs.append(name)
    return list(dict.fromkeys(drugs))


def _extract_primary_endpoint(outcome_measures):
    for om in outcome_measures or []:
        if om.get("type") == "PRIMARY":
            return om.get("measure", "")
    return ""


def _extract_secondary_endpoints(outcome_measures):
    return [om.get("measure", "") for om in (outcome_measures or []) if om.get("type") == "SECONDARY" and om.get("measure")]


def _extract_countries(locations):
    return sorted({loc.get("country") for loc in locations or [] if loc.get("country")})


def _parse_study(study, disease_state):
    proto    = study.get("protocolSection", {})
    ident    = proto.get("identificationModule", {})
    status   = proto.get("statusModule", {})
    design   = proto.get("designModule", {})
    sponsor  = proto.get("sponsorCollaboratorsModule", {})
    conds    = proto.get("conditionsModule", {})
    interv   = proto.get("armsInterventionsModule", {})
    outcomes = proto.get("outcomesModule", {})
    locs     = proto.get("contactsLocationsModule", {})

    for om in outcomes.get("primaryOutcomes", []):
        om["type"] = "PRIMARY"
    for om in outcomes.get("secondaryOutcomes", []):
        om["type"] = "SECONDARY"
    all_outcomes = outcomes.get("primaryOutcomes", []) + outcomes.get("secondaryOutcomes", [])
    interventions = interv.get("interventions", [])
    nct_id = ident.get("nctId", "")

    return {
        "nct_id":              nct_id,
        "title":               ident.get("officialTitle", ""),
        "brief_title":         ident.get("briefTitle", ""),
        "phase":               _map_phase(design.get("phases", [])),
        "status":              _map_status(status.get("overallStatus", "")),
        "sponsor":             sponsor.get("leadSponsor", {}).get("name", ""),
        "lead_sponsor_class":  sponsor.get("leadSponsor", {}).get("class", ""),
        "start_date":          status.get("startDateStruct", {}).get("date", ""),
        "primary_completion":  status.get("primaryCompletionDateStruct", {}).get("date", ""),
        "study_completion":    status.get("completionDateStruct", {}).get("date", ""),
        "enrollment":          design.get("enrollmentInfo", {}).get("count"),
        "conditions":          conds.get("conditions", []),
        "disease_state":       disease_state,
        "therapeutic_area":    _therapeutic_area(disease_state),
        "interventions":       [{"name": i.get("name"), "type": i.get("type")} for i in interventions],
        "drug_names":          _extract_drug_names(interventions),
        "primary_endpoint":    _extract_primary_endpoint(all_outcomes),
        "secondary_endpoints": _extract_secondary_endpoints(all_outcomes),
        "outcome_measures":    all_outcomes,
        "locations":           _extract_countries(locs.get("locations", [])),
        "results_available":   bool(study.get("resultsSection")),
        "study_url":           f"https://clinicaltrials.gov/study/{nct_id}",
        "last_updated":        status.get("lastUpdateSubmitDate", ""),
    }


def fetch_trials_for_disease(disease_state: str) -> Generator[dict, None, None]:
    """Yield parsed trial dicts for a given disease state (Phase 2/3)."""
    condition  = CONDITION_SEARCH_TERMS.get(disease_state, disease_state)
    page_token = None
    fetched    = 0
    logger.info(f"  Fetching ClinicalTrials.gov → {disease_state}")

    while fetched < MAX_TRIALS_PER_DISEASE:
        params = {
            "query.cond":           condition,
            "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING,COMPLETED,NOT_YET_RECRUITING",
            "aggFilters":           "phase:2 3 4",
            "pageSize":             min(100, MAX_TRIALS_PER_DISEASE - fetched),
            "format":               "json",
        }
        if page_token:
            params["pageToken"] = page_token
        try:
            resp = SESSION.get(CLINICALTRIALS_BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error(f"    ClinicalTrials request failed for {disease_state}: {e}")
            break

        studies = data.get("studies", [])
        if not studies:
            break
        for study in studies:
            try:
                yield _parse_study(study, disease_state)
                fetched += 1
            except Exception as e:
                logger.warning(f"    Failed to parse study: {e}")
        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(0.3)

    logger.info(f"    → {fetched} trials fetched for {disease_state}")


def fetch_all_oncology_trials():
    """Fetch trials for all configured disease states."""
    results = {}
    for disease_state in CONDITION_SEARCH_TERMS:
        results[disease_state] = list(fetch_trials_for_disease(disease_state))
        time.sleep(0.5)
    return results
