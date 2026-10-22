# FrailtyScope v0.15: nested preprocessing and regularization selection

## Scope and motivation

The real workstation v0.14 ablation found that adding numeric missingness indicators reduced repeated-development CV Brier loss by 0.002910 (0.136938 to 0.134028), with a gain in all three resampling seeds. Removing all mobility features increased Brier loss. These observations motivated further tests; they are **not independent confirmation** or a clinical outcome.

The v0.13 process selected logistic regression (C = 0.06364630419471101) on NHANES development data, with overall nested procedure Brier loss 0.141275 and fold SD 0.0049365. The v0.14 and v0.15 scores have different model-selection/repetition protocols and cannot be presented as direct evidence that performance has increased by comparing their absolute values.

## Experiment contract

- Only **development** observations are used. The later-cycle evaluation data are never scored.
- The same outer folds score (a) a reference preprocessing pipeline with regularization tuned on each outer training partition, and (b) a variant plus regularization selected solely on that partition's inner folds.
- Both candidates refit imputation, scaling, encoding and logistic/ridge estimation inside training folds. Numeric missingness indicators use sklearn's training-only SimpleImputer(add_indicator=True).
- A fixed margin favors unchanged reference preprocessing when its inner loss is sufficiently close to the optimum. Lower Brier (or other declared development primary loss) is better.
- Repeat scores are development-only, reuse the same people, and are not independent clinical-validation confidence intervals. We explicitly disclose that the candidates were motivated by looking at earlier development results.
- No fitted model is promoted or overwritten. No participant rows, predictions or local experiment metadata are exported to GitHub/Vercel.

## Supported model contracts

This initial focused implementation supports logistic regression with `C` for binary classification and Ridge with `alpha` for regression. Other families must be added via dedicated, validated search spaces and tests; substituting a model name is rejected. Group CV is preserved when the v0.13 strategy includes an approved group column. Temporal/longitudinal inputs remain blocked by existing protocol checks.

## Commands

Install/preflight **without fitting**:

```bash
bash /tmp/frailtyscope-v15/frailtyscope_v15/scripts/install_preprocess_v15.sh
```

Run nested development-only fitting on the **workstation**:

```bash
PYTHONPATH=. .venv/bin/python -m ml.case_preprocess_selection_v15 --run
```

Report: `artifacts/cases/<case_id>/preprocess_selection_v15/<config_hash>/nested_development.json` (ignored, local only).

The report contains counts of inner-selected preprocessing choices and the paired outer-fold losses, with no respondent predictions. A real holdout evaluation or a selected clinical threshold is intentionally **not part of v0.15**. Future promotion requires an independently approved experiment protocol.
