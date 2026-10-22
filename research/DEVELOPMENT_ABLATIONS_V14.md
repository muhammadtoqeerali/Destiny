# FrailtyScope v0.14 — post-selection exploratory development ablations

## Scientific question

Do the default imputation choices or specific feature groups materially change predictive performance of the already-selected v0.13 model on the **development cohort**, when all competing variants are evaluated on exactly matched folds?

## Design contract

- Uses an immutable `selection.json` from v0.13 and verifies dataset, case manifest, strategy configuration, selected family, and selected hyperparameters.
- Never reads held-out outcomes for experiment selection or reports a new holdout metric. All fittings are limited to the development cohort.
- Compares reference imputation with numeric missingness-indicator flags, and controlled omissions of (a) high-missingness walking/stair items, (b) all three mobility measures, and (c) PHQ-9. Predictors are removed consistently from all folds.
- Uses identical stratified (or group-safe) folds for all variants and several predeclared seeds; imputation/scaling/encoding is refitted inside each training fold.
- Models, hyperparameters, outcome definition, split and primary metric are held constant. Results record whole-development out-of-fold primary loss for each seed and paired improvement vs the reference.
- **Exploratory post-selection only**: Hyperparameters and family were already chosen from these development records, so this analysis is not nested, independent validation, statistical superiority evidence or proof of generalization.
- No new model selected or deployed. No clinical or high-performance guarantee. Missingness may be due to survey eligibility or skip patterns, not random absence.
- Evaluation data and identifiers are never exported or persisted; no individual-level model predictions written. Local aggregate report only; **no new public dashboard JSON**.

## Usage

```bash
cd /mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU
PYTHONPATH=. .venv/bin/python -m ml.case_ablation_v14 --plan
PYTHONPATH=. .venv/bin/python -m ml.case_ablation_v14 --run \
  2>&1 | tee ~/frailtyscope-v14-ablation.log
```

The `--run` command **fits models on the workstation** for repeat-fold diagnostics; `--plan` and source-installation do not fit models. Runs refuse to overwrite an existing report, which is versioned by the configuration fingerprint under ignored `artifacts/cases/<case_id>/ablation_v14/`.

For a new assignment, copy `research/cases/ABLATION_TEMPLATE_V14.json`, select a validated v0.13 case, update the source paths and choose medically justified predictor groups. To change folds, seeds or variants, use a **new configuration** and preserve the previous result.

## Recommended future confirmatory steps

Any promising development-stage feature recipe should be incorporated into a **new, predeclared nested model-selection run** and compared with the original strategy across paired outer folds, not adopted directly based on these post-selection OOF results. For repeated visits, censoring, competing risks or site effects, first design appropriate grouped/temporal/survival evaluation. Do not reselect features based on the previously examined NHANES later-cycle results.
