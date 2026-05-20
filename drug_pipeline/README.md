# Oncology Market Intelligence Pipeline

> Automated drug pipeline tracker for oncology therapeutic areas  
> Maintained by **Arpit Kashyap**

A production-grade data pipeline that pulls, enriches, and stores real-time oncology drug pipeline intelligence. Covers **11 disease states** across **4 therapeutic areas**, sourcing data from ClinicalTrials.gov, OpenFDA, and AI-powered web search.

---

## Therapeutic Areas & Disease States

| Therapeutic Area | Disease States |
|---|---|
| **Uro-Oncology** | Prostate Cancer · Bladder Cancer · Renal Cell Carcinoma |
| **Hematologic Oncology** | Multiple Myeloma · Acute Myeloid Leukemia · Chronic Lymphocytic Leukemia |
| **Solid Tumors** | NSCLC · Breast Cancer · Colorectal Cancer |
| **Rare & Orphan** | Myelofibrosis · Cholangiocarcinoma |

---

## Architecture

```
Market_intelligence/
└── drug_pipeline/
    ├── main.py                        # Entry point; orchestrates full pipeline
    ├── requirements.txt
    ├── .github/
    │   └── workflows/
    │       └── monthly_refresh.yml    # GitHub Actions: runs 1st of each month
    ├── pipeline/
    │   ├── config.py                  # Disease states, companies, constants
    │   ├── database.py                # SQLite schema, upserts, query helpers
    │   ├── clinicaltrials.py          # ClinicalTrials.gov API v2 fetcher
    │   ├── fda.py                     # OpenFDA approved drugs fetcher
    │   ├── ai_enricher.py             # Anthropic AI + web search enrichment
    │   └── report.py                  # Markdown + HTML report generator
    ├── data/
    │   ├── oncology_pipeline.db       # SQLite database (auto-created)
    │   └── pipeline.log               # Run logs
    └── reports/
        ├── oncology_pipeline_YYYY-MM-DD.md
        └── oncology_pipeline_YYYY-MM-DD.html
```

---

## Database Schema

```
trials               - ClinicalTrials.gov Phase 2/3 studies
approved_drugs       - FDA-approved oncology drugs
market_intelligence  - AI-enriched per-disease-state intelligence
drug_pipeline        - Deduplicated, normalized pipeline view
refresh_log          - Audit log of all pipeline runs
```

---

## Setup

```bash
cd drug_pipeline
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Usage

```bash
# Full pipeline (all disease states)
python main.py

# AI enrichment only (fastest refresh)
python main.py --ai-only

# Single disease state
python main.py --disease "Prostate Cancer"
python main.py --ai-only --disease "Multiple Myeloma"

# Generate reports from existing database
python main.py --report-only

# View pipeline summary in terminal
python main.py --summary
```

---

## Monthly Automated Refresh (GitHub Actions)

Runs automatically on the **1st of every month at 06:00 UTC**.

Results committed back to the repository:
- `data/oncology_pipeline.db` — updated SQLite database
- `reports/oncology_pipeline_YYYY-MM-DD.html` — HTML report
- `reports/oncology_pipeline_YYYY-MM-DD.md` — Markdown report

### GitHub Secrets Required

| Secret | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key for AI enrichment |

Add at: `Settings -> Secrets and variables -> Actions -> New repository secret`

### Manual trigger

`Actions -> Monthly Oncology Pipeline Refresh -> Run workflow`

Options: `full` | `ai-only` | `trials-only` | `report-only` | specific disease state

---

## Data Sources

| Source | What it provides |
|---|---|
| ClinicalTrials.gov v2 API | Phase 2/3 interventional oncology trials |
| OpenFDA Drugs API | FDA-approved drug applications |
| Anthropic Claude + Web Search | Market intelligence, drug classification, endpoints, competitive landscape |

---

## Querying the Database

```python
from pipeline.database import get_connection, get_pipeline_by_disease, get_market_intelligence

with get_connection() as conn:
    # All drugs for a disease state
    drugs = get_pipeline_by_disease(conn, "Prostate Cancer")
    
    # Market intelligence
    mi = get_market_intelligence(conn, "Multiple Myeloma")
    
    # Custom query
    cur = conn.execute("""
        SELECT drug_name, company, pipeline_stage, primary_endpoint
        FROM drug_pipeline
        WHERE disease_state = 'Non-Small Cell Lung Cancer'
          AND pipeline_stage = 'Phase 3'
        ORDER BY company
    """)
```

---

*Created by Arpit Kashyap | Oncology Market Intelligence Pipeline*
