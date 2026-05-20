"""
Market Intelligence Pipeline — OpenFDA Fetcher
Pulls approved oncology drugs from the FDA Drugs@FDA API.
"""

import time
import logging
import requests

from .config import OPENFDA_BASE_URL, CONDITION_SEARCH_TERMS, DISEASE_STATES

logger = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json", "User-Agent": "OncologyPipelineTracker/1.0"})

FDA_INDICATION_TERMS = {
    "Prostate Cancer":              ["prostate cancer", "castration-resistant"],
    "Bladder Cancer":               ["bladder cancer", "urothelial carcinoma"],
    "Renal Cell Carcinoma":         ["renal cell carcinoma", "kidney cancer"],
    "Multiple Myeloma":             ["multiple myeloma"],
    "Acute Myeloid Leukemia":       ["acute myeloid leukemia", "AML"],
    "Chronic Lymphocytic Leukemia": ["chronic lymphocytic leukemia", "CLL"],
    "Non-Small Cell Lung Cancer":   ["non-small cell lung cancer", "NSCLC"],
    "Breast Cancer":                ["breast cancer", "HER2"],
    "Colorectal Cancer":            ["colorectal cancer", "colon cancer"],
    "Myelofibrosis":                ["myelofibrosis"],
    "Cholangiocarcinoma":           ["cholangiocarcinoma", "bile duct cancer"],
}


def _therapeutic_area(disease_state):
    for area, states in DISEASE_STATES.items():
        if disease_state in states:
            return area
    return "Other"


def _fetch_fda_page(query, skip=0, limit=100):
    try:
        resp = SESSION.get(OPENFDA_BASE_URL, params={"search": query, "limit": limit, "skip": skip}, timeout=30)
        if resp.status_code == 404:
            return {"results": []}
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.warning(f"    FDA request failed: {e}")
        return {"results": []}


def _parse_fda_result(result, disease_state):
    openfda   = result.get("openfda", {})
    app_no    = result.get("application_number", "")
    sponsor   = result.get("sponsor_name", (openfda.get("manufacturer_name") or [""])[0])
    brand_names   = openfda.get("brand_name", [])
    generic_names = openfda.get("generic_name", [])
    substance_names = openfda.get("substance_name", [])

    for product in result.get("products", []):
        brand   = product.get("brand_name", brand_names[0] if brand_names else "")
        generic = generic_names[0] if generic_names else (substance_names[0] if substance_names else "")
        marketing_status = product.get("marketing_status", "")
        if "discontinued" in marketing_status.lower() or "withdrawn" in marketing_status.lower():
            continue
        approval_date = ""
        for sub in result.get("submissions", []):
            if sub.get("submission_type") == "ORIG" and sub.get("submission_status") == "AP":
                approval_date = sub.get("submission_status_date", "")
                break
        return [{
            "drug_name":          generic or brand,
            "brand_name":         brand,
            "company":            sponsor,
            "application_number": f"{app_no}-{product.get('product_number', '0')}",
            "approval_date":      approval_date,
            "indication":         "",
            "disease_state":      disease_state,
            "therapeutic_area":   _therapeutic_area(disease_state),
            "drug_type":          product.get("dosage_form", ""),
            "reference_link":     f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={app_no.replace('NDA','').replace('BLA','').replace('ANDA','').strip()}",
        }]
    return []


def fetch_approved_drugs_for_disease(disease_state):
    """Fetch FDA-approved drugs for a specific disease state."""
    terms = FDA_INDICATION_TERMS.get(disease_state, [disease_state.lower()])
    seen_apps = set()
    all_records = []
    logger.info(f"  Fetching OpenFDA → {disease_state}")
    for term in terms[:2]:
        data = _fetch_fda_page(query=f'products.marketing_status:"Prescription"', limit=50)
        for result in data.get("results", []):
            app_no = result.get("application_number", "")
            if app_no in seen_apps:
                continue
            seen_apps.add(app_no)
            all_records.extend(_parse_fda_result(result, disease_state))
        time.sleep(0.3)
    logger.info(f"    → {len(all_records)} approved drugs fetched for {disease_state}")
    return all_records


def fetch_all_approved_drugs():
    """Fetch approved oncology drugs for all disease states."""
    results = {}
    for disease_state in CONDITION_SEARCH_TERMS:
        results[disease_state] = fetch_approved_drugs_for_disease(disease_state)
        time.sleep(0.5)
    return results
