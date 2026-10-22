# FrailtyScope v0.18 — Development reliability and missingness audit

## Rationale

The v0.17 development-only joint selector reduced Brier and improved AUC/AP versus a tuned reference, but displayed a higher **six-bin descriptive expected calibration error** (ECE) in both repeats. Its mean predicted risk was close to development event prevalence; this does not establish conditional calibration. The chosen v0.16 Random Forest + numeric missingness-indicator recipe warrants a *post-hoc exploratory* probability-calibration experiment. The dataset's missing mobility responses also merit codebook-level audit.

## What runs locally

- `--plan`: reads the ignored dataset's development partition and checks saved v0.16 report, model-file existence, canonical dataset/protocol hashes, group split, and fitting budget. **Does not load the model, train, or score the holdout.**
- `--run`: refits the **fixed v0.16 recipe** on development-fold training rows only. Within every outer training fold, creates inner out-of-fold prediction scores, fits a sigmoid calibrator on these scores and outer-training labels only, then applies it to **outer assessment** predictions from a base model fitted on the whole outer-training fold. Never uses assessment labels to fit a calibrator or model. Base raw probabilities are compared against recalibrated probabilities on paired identical assessment rows.
- Isotonic calibration is optional and automatically **skipped** when fewer than 1,000 calibration rows exist in an outer training fold, to reduce overfitting risk on small samples. This is a conservative reference from scikit-learn's `CalibratedClassifierCV` guidance. The resulting NHANES study is expected to compare identity vs sigmoid, not fit isotonic.
- Reports development-only aggregate Brier, log loss, ROC-AUC, average precision, descriptive binned ECE, prevalence bias, and calibration bins, per repeat. **No threshold is selected and no calibrator/model is promoted.**
- Reports numeric/categorical predictor missingness and event frequencies in missing vs observed groups only when each group has at least the disclosure threshold. Missingness reason is always **unverified** until the CDC codebook or a future dataset's data dictionary is checked.

## Causal and clinical limitations

1. The final v0.16 recipe and parameters were selected using the *same* development cohort before this study. Even with nested calibration fitting, outer-fold results are **post-hoc exploratory** and cannot remove earlier reuse/selection bias.
2. Repeated folds involve the same participants; apparent gains are not independent tests and have no survey-design-aware confidence interval.
3. A calibrator trained on OOF predictions from smaller inner-fold models is applied to probabilities from a model fitted on all outer training rows, potentially causing distribution differences. This is common in cross-fitting but must be inspected.
4. ECE depends on binning; don't promote a calibrator based on ECE alone. Study Brier, log loss, calibration intercept/slope, subgroup miscalibration and decision utility before any clinical interpretation.
5. A missingness indicator may reflect survey routing, respondent behavior, or health status. **Missing versus observed differences cannot diagnose MAR, MCAR, MNAR or a skip mechanism.** Consult question routing, valid/unavailable codes and NHANES documentation before feature policy changes.
6. Never apply standard shuffled row CV to repeated-person, longitudinal, censored survival or time-shifted outcomes. Use the corresponding design-specific protocol.

## Reuse for a new assignment

No v0.13–v0.15 experiment is a prerequisite. Provide a case-specific v0.10 manifest, v0.13 strategy protocol, v0.16 joint configuration, *completed workstation v0.16 selection*, and a v0.18 configuration with matching hashes and saved selected pair. Adjust the task design and data contract rather than reusing NHANES-specific features or labels.

## Publication boundary

Raw data, study reports, predictions, IDs, fitted models and fitted calibrators remain in ignored `data/` and `artifacts/`. Source-only publication runs pure tests and validates the local metadata, with an explicit uppercase YES confirmation. No public JSON/dashboard export in this version.
