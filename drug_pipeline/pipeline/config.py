"""
Market Intelligence Pipeline — Configuration
Oncology therapeutic areas, disease states, and pipeline constants.
"""

# ── Therapeutic Areas & Disease States ────────────────────────────────────────
DISEASE_STATES = {
    "Uro-Oncology": [
        "Prostate Cancer",
        "Bladder Cancer",
        "Renal Cell Carcinoma",
    ],
    "Hematologic Oncology": [
        "Multiple Myeloma",
        "Acute Myeloid Leukemia",
        "Chronic Lymphocytic Leukemia",
    ],
    "Solid Tumors": [
        "Non-Small Cell Lung Cancer",
        "Breast Cancer",
        "Colorectal Cancer",
    ],
    "Rare & Orphan": [
        "Myelofibrosis",
        "Cholangiocarcinoma",
    ],
}

ALL_DISEASE_STATES = [ds for states in DISEASE_STATES.values() for ds in states]

CONDITION_SEARCH_TERMS = {
    "Prostate Cancer":              "prostate cancer",
    "Bladder Cancer":               "bladder cancer",
    "Renal Cell Carcinoma":         "renal cell carcinoma",
    "Multiple Myeloma":             "multiple myeloma",
    "Acute Myeloid Leukemia":       "acute myeloid leukemia",
    "Chronic Lymphocytic Leukemia": "chronic lymphocytic leukemia",
    "Non-Small Cell Lung Cancer":   "non-small cell lung cancer",
    "Breast Cancer":                "breast cancer",
    "Colorectal Cancer":            "colorectal cancer",
    "Myelofibrosis":                "myelofibrosis",
    "Cholangiocarcinoma":           "cholangiocarcinoma",
}

KEY_COMPANIES = [
    "AstraZeneca", "Bristol-Myers Squibb", "Johnson & Johnson", "Janssen",
    "Merck", "Pfizer", "Novartis", "AbbVie", "Roche", "Genentech",
    "Eli Lilly", "Gilead", "Amgen", "Regeneron", "Sanofi",
    "Daiichi Sankyo", "Seagen", "Incyte", "Blueprint Medicines",
    "Mirati", "Karuna", "Merus", "Relay Therapeutics",
]

PHASE_MAPPING = {
    "PHASE1":       "Phase 1",
    "PHASE2":       "Phase 2",
    "PHASE3":       "Phase 3",
    "PHASE4":       "Phase 4 / Post-Market",
    "NA":           "N/A",
    "EARLY_PHASE1": "Early Phase 1",
}

STATUS_MAPPING = {
    "RECRUITING":               "Recruiting",
    "ACTIVE_NOT_RECRUITING":    "Active, Not Recruiting",
    "COMPLETED":                "Completed",
    "TERMINATED":               "Terminated",
    "WITHDRAWN":                "Withdrawn",
    "NOT_YET_RECRUITING":       "Not Yet Recruiting",
    "SUSPENDED":                "Suspended",
    "ENROLLING_BY_INVITATION":  "Enrolling by Invitation",
    "APPROVED_FOR_MARKETING":   "Approved",
}

MARKET_SIZE_BASELINE = {
    "Prostate Cancer":              {"size_usd_bn": 12.4, "cagr_pct": 7.2,  "patients_us": 288_000},
    "Bladder Cancer":               {"size_usd_bn": 4.1,  "cagr_pct": 6.8,  "patients_us": 83_000},
    "Renal Cell Carcinoma":         {"size_usd_bn": 5.8,  "cagr_pct": 8.1,  "patients_us": 79_000},
    "Multiple Myeloma":             {"size_usd_bn": 24.3, "cagr_pct": 9.4,  "patients_us": 162_000},
    "Acute Myeloid Leukemia":       {"size_usd_bn": 3.9,  "cagr_pct": 7.6,  "patients_us": 21_000},
    "Chronic Lymphocytic Leukemia": {"size_usd_bn": 8.7,  "cagr_pct": 8.9,  "patients_us": 199_000},
    "Non-Small Cell Lung Cancer":   {"size_usd_bn": 31.2, "cagr_pct": 10.3, "patients_us": 236_000},
    "Breast Cancer":                {"size_usd_bn": 28.6, "cagr_pct": 9.7,  "patients_us": 310_000},
    "Colorectal Cancer":            {"size_usd_bn": 14.8, "cagr_pct": 6.4,  "patients_us": 152_000},
    "Myelofibrosis":                {"size_usd_bn": 2.3,  "cagr_pct": 11.2, "patients_us": 21_000},
    "Cholangiocarcinoma":           {"size_usd_bn": 1.4,  "cagr_pct": 12.1, "patients_us": 8_000},
}

CLINICALTRIALS_BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
OPENFDA_BASE_URL        = "https://api.fda.gov/drug/drugsfda.json"
MAX_TRIALS_PER_DISEASE  = 100
INCLUDED_PHASES = ["Phase 2", "Phase 3", "Phase 4 / Post-Market", "Approved"]
AI_MODEL = "claude-sonnet-4-20250514"
