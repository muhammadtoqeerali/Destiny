# FrailtyScope v0.5 — Five outcome domains and advanced ML

## Delivered in this release

- Admin: multi-outcome research front page, benchmark and validation detail, published **HUNT4 70+ aggregate context**, HUNT access/readiness checklist; original preprocessing/data/model evaluation remains under **Original pipeline**.
- Doctor: new **Health outlook** tab for fictional patients, 5 outcomes with independently fitted model outputs, 3 simulated pre-baseline observation points. No clinical prediction or diagnosis.
- Machine learning: five fabricated 12-month outcomes × 4 algorithms = 20 model configurations; patient-disjoint 60/20/20 train/validation/test split; selection by validation Brier, held-out ROC-AUC, AP, Brier, accuracy at 0.5, sensitivity/recall, specificity, precision, F1 and confusion matrices.
- Actual *algorithm* execution verified for XGBoost 3.1.3 and CatBoost 1.2.8, alongside LR and histogram boosting. Real SHAP permutation explanation summaries were computed for each of the five selected models and are public **only for synthetic examples**; detailed local SHAP work files remain gitignored. Global summaries currently use only five simulated cases per outcome and should be considered exploratory.
- Approved HUNT **data contract** and local-only importer which handles 12-month ascertainment, incomplete follow-up and early death as censoring. It does NOT grant access or retrieve data.

## No HUNT individual-level data

Only HUNT's **published cohort counts** are factual real-HUNT aggregate data in the public dashboard. Neither clinical outcomes nor feature distributions in this release are from HUNT. All individual patient cases and prognosis-like scores are simulated. No new patient data should be entered into this public app.

## Train the synthetic experiment on your workstation

```bash
cd /mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU
source .venv/bin/activate
pip install -r requirements-advanced.txt
python -m ml.advanced_multitarget --n 6000 --artifact-dir artifacts
python -m ml.explain_shap --outcome fracture_within_12m --output artifacts/shap_synthetic_fracture.json
python -m pytest -q tests/test_multidimensional.py
```

The published `multioutcome-demo.json` is a precomputed, reproducible **synthetic-only** snapshot. Regenerate it only from synthetic data. `artifacts/` is ignored and must never go to GitHub/Vercel.

## Known limitations

- *Longitudinal visualization* is based on three generated pre-baseline observation points. It is not a fit of a longitudinal model and not actual HUNT time series.
- Random sample split is appropriate for this software proof-of-concept only, not historical/temporal prospective external validation.
- Sparse artificial events can make accuracy misleading (e.g., fracture). Evaluate ROC-AUC, AP and calibration.
- Five outcomes are independent classifiers; no competing-risk survival likelihood, multi-state modeling, or real event-time analysis yet.
- Real approved HUNT data remain inaccessible without REK, DAC, agreement, project-scoped approvals and secure computing access.
- Admin password `admin123` remains a DEMO ONLY gate, never a real medical data security control.

## Source and provenance

- https://academic.oup.com/ije/article/55/2/dyag011/8490101
- https://www.ntnu.edu/hunt/dataaccess
- https://www.ntnu.edu/digitalfrailcare
