# FrailtyScope — Explainable Ageing & Health Intelligence

> **Independent, synthetic-only research prototype. No affiliation, endorsement, HUNT patient data, actual HUNT outcome results, or clinical approval is implied.**

This project is stored in the private working directory / GitHub repo named `Destiny`, but the **public dashboard branding is FrailtyScope**.

## Phase 2 highlights

- 6,000 reproducibly generated simulated records with artificial 12-month fall-event outcomes.
- Training-only imputation + encoding to avoid basic preprocessing leakage.
- 60 / 20 / 20 stratified person-level train/validation/test partitions (demonstration, **not** temporal or external validation).
- Six configurations: regularized logistic regression, random forest, histogram gradient boosting × clinical or expanded feature groups.
- Algorithm and feature group chosen **only by validation Brier score**; held-out test set evaluated afterwards.
- ROC-AUC, average precision, Brier scores, 95% fixed-model test-set percentile bootstrap intervals, calibration bins, exploratory decision curve, age/sex breakdown, core comparator, permutation importance and local one-feature contrasts.
- Research protocol and variable mapping template prepared for **future approved** HUNT access.
- Next.js dashboard with data-readiness tab, model uncertainty and model comparison, supported by PUBLIC SYNTHETIC JSON only.

### Scientific limitations

Synthetic outcomes are invented and do not estimate actual fall risk in HUNT or other populations. Feature names are demonstrative, NOT HUNT variable IDs. Local explanations are perturbations rather than SHAP values; they are not causal or additive. Decision-curve analysis uses artificial outcomes and must not inform clinical decisions. Fixed-model bootstrap intervals are not full model-development uncertainty. Model selection is not tuned on the held-out set, but evaluating several variants does not remove risks of optimistic validation performance. No approved HUNT dataset is available to this project.

## Run on the Linux workstation

Copy the release into `/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU/` without copying stored files, Python environments, or Git metadata from the extracted package.

```bash
cd /mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU
bash scripts/phase2_upgrade.sh 2>&1 | tee phase2-run.log
# After the training and build succeed:
cd web
npm run dev -- -p 3001
```

If port 3001 is occupied by the previously running Next.js server, stop the old dev server with Ctrl+C or run the new one on a different port. Windows laptop browser requires SSH forwarding, e.g. `ssh -N -L 13001:127.0.0.1:3001 YOUR_EXISTING_SSH_ALIAS` in PowerShell. The tunnel terminal remains open. Never put passwords or SSH private keys in shared logs.

### Deploy on Vercel

The repository can remain named Destiny. Import it in Vercel, **set Root Directory to `web`**, and deploy only after checking `web/public` contains synthetic-only assets. DO NOT expose sensitive HUNT files, person-level health data, trained confidential models, protected logs or credentials. No inference API is part of this public release.

### Directory structure

- `ml/simulate.py` — synthetic generator
- `ml/train.py` — six-model ablation and reproducible test/evaluation reports
- `ml/schema.py` — illustrative feature names and labels
- `tests/test_pipeline.py` — pipeline correctness and data safety checks
- `web/app` — dashboard pages and styling
- `web/public/data/demo.json` — synthetic-only artifact for public demonstration
- `research/` — research protocol, study mapping wishlist and sources
- `artifacts/` — ignored model and run report generated locally; never commit

## Research endpoints to clarify with the institution

Define the actual data provenance, ethics approvals, eligible population, baseline/index date, follow-up window, ascertainment of outcomes, causes of missingness and linkage. Determine whether outcomes are measured repeatedly and deaths create competing risk before designing a time-to-event or recurrent-event framework. Use longitudinal/temporal/external validation only when possible and justified with the approved dataset; **never present this synthetic random split as temporal validation.**

## Primary public sources

- NTNU Digi-FrailCare: https://www.ntnu.edu/digitalfrailcare
- HUNT data access: https://www.ntnu.edu/hunt/data
- HUNT variable catalogue: https://hunt-db.medisin.ntnu.no/hunt-db/
- Cohort Profile HUNT4 70+ (published 19 Feb 2026): https://academic.oup.com/ije/article/55/2/dyag011/8490101
- TRIPOD+AI: https://www.bmj.com/content/385/bmj-2023-078378

**Safety:** no clinical use; no patient-level HUNT data in git, public site, analytics, demo export, or unapproved workstation.
