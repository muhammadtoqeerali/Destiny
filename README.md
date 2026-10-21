# FrailtyScope — Real NHANES ageing-health research

**Active cohort: real CDC NHANES 2011–2014 public-use survey plus 2019 public-use linked mortality data. Not HUNT.**

FrailtyScope is an independent, nonclinical research demonstrator. The Admin Portal shows fully aggregated statistics and an auditable pipeline, and the Doctor Portal provides plain-language cohort-level interpretation. **No individual participant records or model predictions are published.**

## Workstation research

- `ml/realdata_nhanes.py` — official file acquisition, local preprocessing and linking.
- `ml/realdata_train.py` — logistic regression, histogram gradient boosting, XGBoost, CatBoost, validation-selected model and screening threshold, held-out later-cycle metrics.
- `ml/longitudinal_contract.py` — dated endpoint framework for future cohort transitions.
- `ml/approved_hunt_adapter.py` — offline authorized data mapping, not a HUNT downloader.
- `tests/test_real_nhanes.py` — ingestion, censoring and model tests (small artificial **unit-test fixtures** do not constitute a research dataset).
- `scripts/export_nhanes_aggregate.py` — strictly allowlisted aggregate-only public JSON export.

Run the real benchmark with `bash scripts/run_real_nhanes.sh "$PWD"` after installing `requirements-advanced.txt`. Actual public records, linked fields and saved artifacts remain local in ignored `data/` and `artifacts/` directories.

## Dashboard

Vercel project root is `web`. The public JSON at `web/public/data/nhanes-aggregate.json` is derived solely from the locally generated `artifacts/realdata_nhanes/report.json`. Never publish person-level data, NHANES ID fields, local model binaries, or future approved HUNT data.

For migration of an older synthetic release, see `README_MIGRATION.md`. Research limitations and source documentation are described in the Admin Portal and `research/`.
