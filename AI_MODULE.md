# VendorIQ — Developer 2 Module Documentation (AI, ML & Document Intelligence)

## 1. Module Architecture Overview

VendorIQ is an AI-powered supplier qualification and batch intelligence platform. As **Developer 2**, this module provides the document extraction pipeline, deterministic validation engine, supplier historical track-record analytics, machine learning batch risk prediction, and Kimi K3 technical reasoning synthesis within a **single unified FastAPI backend**.

```
                  React / Vite Frontend (Developer 4)
                                  │
                                  ▼
                     Shared FastAPI Backend
       ┌──────────────────────────┴──────────────────────────┐
       │                                                     │
Developer 1 Infrastructure                             Developer 2 Modules (YOU)
• Neon PostgreSQL (SQLAlchemy)                         • app/services/document_service.py
• Authentication & Base Schemas                        • app/services/validation_service.py
• Core Models (Vendor, Batch, Material, Docs)          • app/services/vendor_history_service.py
                                                       • app/services/prediction_service.py
                                                       • app/services/kimi_service.py
                                                       • app/ml/ (Model, Features, Training)
                                                             │
                                                             ▼
                                                Developer 3 Decision Engine
                                                • Approved / Rejected / Needs Review
                                                • SMTP Notifications & Audit Log
```

---

## 2. Document Processing (`app/services/document_service.py`)

### Supported File Formats:
- **PDF** (via `pypdf`)
- **CSV** (via Python `csv` / text streams)
- **XLSX** (via `openpyxl`)
- **DOCX** (via `python-docx`)
- **TXT** (UTF-8 with resilient decoding)

### Supported Document Types:
`COA`, `SDS`, `GMP`, `SPECIFICATION`, `TEST_REPORT`, `COMPLIANCE`, `OTHER`.

### COA Extraction Scope:
The extraction engine extracts laboratory analytical figures without hallucinating:
- `batch_number`: Regex & tabular key-value parser for batch/lot IDs.
- `material`: Product chemical/trade name.
- `purity`: Assay/purity percentage (e.g. `99.4%`).
- `moisture`: Water content / Loss on Drying (LOD) percentage.
- `heavy_metals`: PPM values or detection limits (e.g., `< 5 ppm`, `ND`).
- `microbial_parameters`: Total Aerobic Microbial Count (TAMC), Total Yeast/Mold (TYMC), E. coli.
- `test_date`, `manufacturing_date`, `expiry_date`: Standardized ISO date parsing.
- `laboratory`: Certifying testing facility name.

### Safety & Integrity Rules:
1. **NEVER hallucinate missing information**: If a parameter cannot be found, it is recorded as `None` and added to `missing_fields`.
2. **Failure Handling**: If critical parameters (`purity` or `batch_number`) are unextractable, or if document parsing fails, document status is set to `NEEDS_REVIEW` (never crash).

---

## 3. Validation Service (`app/services/validation_service.py`)

Validates batch test data against **configurable company & material specifications** from the database (not hardcoded statutory limits).

### Validation Checks:
1. **Documentation Completeness**: Verifies mandatory documents (COA, SDS, GMP) are attached.
2. **COA Analytical Parameters**:
   - Purity: `actual purity >= material.purity_min` (e.g. actual `99.3%` vs `>=99.0%` -> `PASS`, `98.2%` -> `FAIL`).
   - Moisture: `actual moisture <= material.moisture_max` (e.g. `<= 0.5%`).
   - Contaminant Limits: `heavy_metals <= material.heavy_metals_max_ppm`.
   - Microbial Limits: `TAMC <= material.microbial_limit_cfu_g`.
3. **Traceability**:
   - Matches COA batch number against system batch record.
   - Verifies manufacturing date <= test date <= expiry date.
4. **Certificate Validity**: Validates vendor GMP certificate expiration date against the evaluation date.
5. **Storage Specifications**: Verifies SDS explicitly defines handling and temperature storage conditions.

### Status Outputs:
- Individual checks: `PASS`, `FAIL`, `MISSING`, `NEEDS_REVIEW`.
- Overall status: `PASS` (all required pass), `FAIL` (any failure), or `NEEDS_REVIEW` (missing required information).

---

## 4. Vendor History Analysis (`app/services/vendor_history_service.py`)

Reads past batches and document metadata directly from Neon PostgreSQL via SQLAlchemy queries. Never hardcodes demo vendor statistics.

### Calculated Historical Metrics:
- `previous_batches`: Total completed historical batches.
- `approval_rate`: Ratio of past batches with `status == "APPROVED"`.
- `rejection_rate`: Ratio of past batches with `status == "REJECTED"`.
- `average_purity`: Historical arithmetic mean of reported purity.
- `purity_variance`: Sample variance ($s^2$) of past batch purity.
- `documentation_completeness`: Historical compliance rate of supplier documentation.
- `delivery_reliability`: Supplier on-time performance rate (0.0 to 1.0).
- `incident_count`: Historical rejections and logged quality deviations.
- `average_lead_time`: Mean duration (days) from order to delivery.
- `price_variance`: Variance in unit pricing across past batches.
- `capacity`: Supplier declared monthly production volume.
- `comparison_notes`: Purity delta vs historical mean, capacity utilization warnings.

### Edge Case Handling:
- **New Vendor (0 previous batches)**: Returns structured defaults, flags `status = "INSUFFICIENT_HISTORY"`, prevents division-by-zero.
- **Single Batch (1 previous batch)**: Variance gracefully defaults to `0.0`.

---

## 5. Machine Learning Risk Model (`app/ml/`)

Deterministic `RandomForestClassifier` trained using `scikit-learn`.

### Feature Vector (12 Deterministic Features):
1. `quality_score` (0.0 - 100.0, composite validation score)
2. `purity` (numerical percentage)
3. `purity_variance` (historical statistical variance)
4. `document_completeness` (0.0 - 1.0)
5. `certification_status` (numerical encoding: GMP_CERTIFIED=1.0, ISO_CERTIFIED=0.8, PENDING=0.4, EXPIRED/NONE=0.0)
6. `delivery_reliability` (0.0 - 1.0)
7. `rejection_rate` (0.0 - 1.0)
8. `incident_count` (integer count >= 0)
9. `lead_time` (days)
10. `capacity` (units/month)
11. `price_variance` (price variance vs baseline)
12. `historical_approval_rate` (0.0 - 1.0)

### Outputs:
- `risk_score`: Calibrated integer/float from `0.0` (safest) to `100.0` (highest risk).
- `risk_probability`: Calibrated float from `0.0` to `1.0`.
- `risk_level`: Standardized categorical mapping:
  - `LOW`: `risk_score < 25.0`
  - `MEDIUM`: `25.0 <= risk_score < 50.0`
  - `HIGH`: `50.0 <= risk_score < 75.0`
  - `CRITICAL`: `risk_score >= 75.0`
- `risk_factors`: List of human-readable root causes (e.g., purity below spec, expired GMP certificate).
- `feature_contributions`: Feature importance scores for auditable transparency.

### Synthetic Development Data Disclaimer:
> **NOTICE**: Training dataset script located at `app/ml/training/train_risk_model.py` generates **SYNTHETIC DEVELOPMENT DATA ONLY** for local development, model serialization (`risk_model.joblib`), and offline benchmarking. Never represent this synthetic training data as production ground truth.

---

## 6. Kimi K3 Reasoning Integration (`app/services/kimi_service.py`)

Kimi K3 acts **EXCLUSIVELY as the natural-language explanation and reasoning layer**.

### Responsibilities:
- Receives technical context: Vendor info, Material specs, Batch parameters, Validation results, Vendor history, ML prediction, Risk factors.
- Returns structured JSON:
  ```json
  {
      "summary": "...",
      "key_findings": ["..."],
      "risk_factors": ["..."],
      "business_impact": ["..."],
      "recommended_actions": ["..."],
      "decision_explanation": "..."
  }
  ```

### Strict Architectural Boundaries:
- Kimi **MUST NOT** modify or recalculate the ML risk score.
- Kimi **MUST NOT** override deterministic validation check failures.
- Kimi **MUST NOT** invent missing data or make unsupported statutory claims.
- The final business decision (`APPROVED` / `REJECTED` / `NEEDS_REVIEW`) belongs to Developer 3's Decision Engine.

### Resilient Failure Handling:
If the Kimi API times out, returns HTTP 4xx/5xx, is unreachable, or if `KIMI_API_KEY` is not configured:
- **The ML prediction STILL SUCCEEDS.**
- Kimi status is set to `kimi_status = "FAILED"`.
- A deterministic fallback analysis is populated.
- **The pipeline NEVER crashes.**

---

## 7. API Endpoints

### 1. `POST /api/batches/{id}/process`
Extracts all attached documents, runs deterministic validation, computes historical vendor metrics, and persists intermediate outputs to `batch_intelligence`.

**Response Example:**
```json
{
  "batch_id": 1,
  "batch_number": "BATCH-2026-X01",
  "validation_result": {
    "overall_status": "PASS",
    "checks": [
      {
        "name": "purity",
        "status": "PASS",
        "expected": ">=99.0%",
        "actual": 99.4,
        "reason": "Actual purity 99.4% satisfies specification requirement of >=99.0%."
      }
    ],
    "missing_information": [],
    "warnings": []
  },
  "vendor_history": {
    "vendor_id": 1,
    "previous_batches": 12,
    "approval_rate": 0.9167,
    "rejection_rate": 0.0833,
    "average_purity": 99.25,
    "purity_variance": 0.045,
    "documentation_completeness": 0.95,
    "delivery_reliability": 0.96,
    "incident_count": 1,
    "average_lead_time": 13.5,
    "price_variance": 0.22,
    "capacity": 150000.0,
    "comparison_notes": {}
  },
  "extracted_documents": [
    {
      "document_id": 10,
      "filename": "coa_sample.pdf",
      "document_type": "COA",
      "status": "PROCESSED",
      "extracted_data": {
        "batch_number": "BATCH-2026-X01",
        "purity": 99.4,
        "moisture": 0.28
      },
      "missing_fields": [],
      "error": null
    }
  ],
  "message": "Batch documents processed and validated successfully."
}
```

### 2. `POST /api/batches/{id}/predict-risk`
Assembles deterministic feature vector, evaluates the ML model, queries Kimi K3 for reasoning synthesis, and records predictions.

**Response Example:**
```json
{
  "batch_id": 1,
  "batch_number": "BATCH-2026-X01",
  "risk_prediction": {
    "risk_score": 14.2,
    "risk_probability": 0.142,
    "risk_level": "LOW",
    "risk_factors": [],
    "feature_contributions": {
      "quality_score": 0.21,
      "purity": 0.18,
      "certification_status": 0.15
    }
  },
  "kimi_analysis": {
    "summary": "Batch BATCH-2026-X01 meets analytical and regulatory specifications.",
    "key_findings": [
      "Assay purity measured at 99.4%, exceeding required minimum.",
      "Vendor holds active GMP certification with 96% delivery reliability."
    ],
    "risk_factors": [],
    "business_impact": [
      "Low financial or recall risk; recommended for standard release."
    ],
    "recommended_actions": [
      "Clear batch for warehouse intake."
    ],
    "decision_explanation": "Low risk rating assigned based on strong historical supplier performance and full monograph compliance.",
    "kimi_status": "SUCCESS"
  },
  "features_used": {
    "quality_score": 100.0,
    "purity": 99.4,
    "purity_variance": 0.045
  },
  "message": "Risk prediction and AI reasoning generated successfully."
}
```

---

## 8. Database Integration (`batch_intelligence` table)

To ensure zero conflicts with Developer 1's models, Developer 2's persistence is isolated in a dedicated table `batch_intelligence` linked via Foreign Key to `batches.id`:

```sql
CREATE TABLE batch_intelligence (
    id SERIAL PRIMARY KEY,
    batch_id INTEGER UNIQUE NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
    validation_result JSON,
    vendor_history JSON,
    ml_features JSON,
    ml_prediction JSON,
    kimi_analysis JSON,
    kimi_status VARCHAR(50) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Developer 1's `documents` table stores extracted data in `extracted_data` (JSON) and `status` (`PROCESSED`, `NEEDS_REVIEW`, `FAILED`).

---

## 9. Environment Variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | string | `sqlite:///./vendoriq.db` | Neon PostgreSQL connection string in production |
| `KIMI_API_KEY` | string | `None` | API key for Kimi K3 (Moonshot API) |
| `KIMI_API_BASE` | string | `https://api.moonshot.cn/v1` | Base URL for Kimi K3 |
| `KIMI_MODEL` | string | `moonshot-v1-8k` | Kimi model identifier |
| `KIMI_TIMEOUT_SECONDS` | float | `30.0` | Request timeout for external reasoning calls |

---

## 10. Testing & Verification

Run the complete test suite:
```bash
python -m pytest -v
```

### Coverage:
- 35 unit and integration tests across:
  - Document extraction (PDF, CSV, XLSX, DOCX, TXT)
  - Missing field handling and `NEEDS_REVIEW` flagging
  - COA parameter matching
  - Validation pass, fail, expired certs, and doc completeness
  - Vendor history statistics and zero-history edge cases
  - Feature building and Random Forest risk predictions
  - Kimi success, timeout, HTTP error, and malformed response fallbacks
  - API endpoint integration tests (`/health`, `/process`, `/predict-risk`)
