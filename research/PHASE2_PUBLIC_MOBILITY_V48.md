# FrailtyScope — NTNU Postdoctoral Interview: Phase 2 / 3

## Objective (fixed)
Demonstrate expert, reproducible tabular ML on **one openly accessible ageing-relevant dataset**, with careful source semantics, train-only preprocessing, fair model comparison, calibrated probabilities and interpretable explanations, then present results clearly. **No new hospital/clinical-product features.** Phase 1 / v0.47 interview UI is already published. Phase 3 begins only once this real experiment has run, been reviewed and its permitted aggregates are ready.

## Case: `public_nhanes_mobility_2015_2018_v48` — DIFFERENT from old blocked mortality case
- **Official open source:** CDC NHANES public-use XPT. 2015–16 ('I') model development, 2017–18 ('J') reserved later-cycle evaluation. Six files per survey cycle: `DEMO`, `PFQ`, `BMX`, `MCQ`, `DIQ`, `DPQ`.
- **Cohort:** Age ≥65. NHANES public ages 80+ are top-coded to 80. The files cover different participants, **not longitudinal observation of the same people**.
- **Task:** `PFQ061B` quarter-mile walking difficulty: `1` = none vs `2,3,4` = some/much/unable. Codes `5` (does not do activity), `7` (refused), `9` (don't know) and NA are **excluded**, not treated as negative. `PFQ054=1` denotes walking equipment; the item was **not administered** by the questionnaire routing and is excluded. The label is **current self-reported mobility difficulty**, NOT future frailty, no diagnosis, no HUNT claim.
- **Inputs:** age, sex, BMI, PHQ-9 total (only nine valid `0..3` symptom answers), arthritis, heart failure, stroke and diagnosed diabetes. Disease items use `1=yes, 2=no`; borderline diabetes `3` and refusals are **missing**, never fabricated as no. All PFQ items are *excluded* from the predictor set to avoid direct outcome leakage.
- **Experiment:** Split 2015–16 80% fitting / 20% validation, stratified and participant-disjoint. Three-fold stratified inner CV with fixed seed; transformers fitted inside each fold. Search tuned logistic, random forest and histogram boosting plus XGBoost/CatBoost if installed. All candidates see the same CV and validation. A dummy-prior baseline is mandatory. Select lowest **validation Brier** with deterministic tie-break. Compute permutation importance on **validation only**. Evaluate the winning model once on 2017–18 (ROC-AUC, average precision, Brier, log loss, sensitivity/specificity at fixed 0.5, calibration bins, descriptive subgroups, naive bootstrap intervals).
- **Limits:** One current self-report questionnaire outcome; missingness and equipment-routing selection; MEC/PHQ nonresponse; public age topcoding; no NHANES complex-survey design-based CI; raw record bootstrap intervals **not** valid design-based variance. 2017–18 is later survey-cycle transport (not untouched external prospective frailty validation). Weighted Brier is *exploratory only* and cannot replace survey-correct inference.
- **Security/source separation:** Does not read or alter `nhanes_mortality_v10`, its holdout, private files or saved models. New XPT files and aggregate experiment results must remain outside Git checkout, e.g. `.../NTNU-restricted/nhanes_mobility_public`. No model binaries, participant rows or individual probabilities are exported. Clinical inference stays blocked.

## One focused execution after source-only installer

```bash
cd /mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU
DATA_ROOT=/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU-restricted/nhanes_mobility_public
PYTHONPATH=. .venv/bin/python -m ml.public_mobility_v48 --contract
# First obtain 12 public XPT files directly from CDC (only if absent):
PYTHONPATH=. .venv/bin/python -m ml.public_mobility_v48 --data-root "$DATA_ROOT" --download
# Then run the REAL benchmark (never in GitHub CI):
PYTHONPATH=. .venv/bin/python -m ml.public_mobility_v48 --data-root "$DATA_ROOT" --run
```

Official file URL pattern: `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{2015|2017}/DataFiles/{DEMO|PFQ|BMX|MCQ|DIQ|DPQ}_{I|J}.XPT`.
If the workstation blocks automated downloads, use the [CDC 2015–2016](https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2015) and [CDC 2017–2018](https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2017) component pages. Save matching public XPT files into `$DATA_ROOT/raw/` with the exact names. Do not upload participant-level XPT to ChatGPT or Vercel.

Local outputs:
- `$DATA_ROOT/results/mobility_aggregate_v48.json` — **aggregate** cohort description, separate validation leaderboard, later-cycle selected-model metrics, reliability, sensitivity and feature importance.
- `$DATA_ROOT/results/mobility_report_v48.md` — concise scientific results for preparing the interview presentation.

The web UI is **deliberately not changed** until the local real-data experiment has run and is reviewed. Synthetic Phase 1 scores must retain their fictional label; do not replace them with unverified real metrics or publish participant-level examples. The next implementation is to wire **safe reviewed aggregates**, not data records, into Admin results and maintain fictional demonstration profiles in Doctor.

## Interview explanation in 30 seconds
'I selected a public ageing-relevant NHANES task to avoid waiting for restricted HUNT access. I audited the official source coding—including structural skips and invalid answers—created a clean current mobility label, and kept questionnaire outcome items out of the predictors. I compared a baseline, linear and nonlinear models with identical leakage-safe preprocessing and tuning, chose by validation calibration error and evaluated once on a later survey cycle. I separately measured discrimination, probability calibration and uncertainty; I can explain both the selected model and its limitations. I would apply the same audited protocol to HUNT only after target definition, source harmonization and access approval.'

**Do not say we predicted future frailty** on these cross-sectional surveys. Future longitudinal prediction requires true follow-up and target definition.

## v0.48.1 — Real-data coverage correction after the first workstation run

The initial public-data run selected CatBoost (validation Brier 0.15571, later-cycle ROC-AUC 0.68597), **but emitted repeated `SimpleImputer` warnings: `phq9_score` had no observed values in the fit**. Those scores are preliminary. Do not present them as a final validated benchmark.

The corrected pipeline now performs a deterministic **input-availability audit** for the 2015–2016 and 2017–2018 cohorts. It displays only aggregate counts of valid DPQ items, complete 9-item scores, and observations per proposed predictor. The audit does not fit a model or export rows. Any candidate predictor with fewer than **20 actually observed responses** in either cycle is explicitly removed from *both* cycles' model matrices before fitting. The actual model feature list and each exclusion are recorded in the aggregate JSON and markdown report. Age and sex must remain available or the pipeline stops. There is no silent scikit-learn feature removal.

We do **not yet know** why the genuine data led to zero valid PHQ-9 values in the first run. The new audit differentiates “every DPQ item missing” from “some individual items observed, but no complete nine-item score.” Investigate any unexpectedly low coverage before drawing substantive conclusions. No PHQ-9 scores are guessed or filled from invalid questionnaire codes.

The first run already examined 2017–2018 model performance. **All subsequent evaluations on that cycle must be labeled a previously inspected repeat/sensitivity evaluation, not a fresh untouched holdout.** Model choice continues to use the 2015–2016 development validation set only. If a truly untouched confirmatory comparison is later required, a new independent dataset/protocol is necessary.

Only reuse the 12 existing public XPT files. Keep all input files and experiment output outside the Git checkout. Retain the pre-correction aggregate results under a separate name for provenance. Do not copy participant records or per-person probabilities into GitHub or the Doctor Portal. The original 2011–2014 mortality case remains blocked and untouched.

```bash
DATA_ROOT=/mnt/hdd16T/ToqeerHomeBackup/toqeer/NTNU-restricted/nhanes_mobility_public
PYTHONPATH=. .venv/bin/python -m ml.public_mobility_v48 --data-root "$DATA_ROOT" --audit-coverage
PYTHONPATH=. .venv/bin/python -m ml.public_mobility_v48 --data-root "$DATA_ROOT" --run
```


## v0.48.2 — SAS XPORT zero decoder correction (critical)

The public CDC DPQ codebook uses **0 = Not at all** for each PHQ-9 item.
The pandas SAS XPORT decoder in the tested environment may decode an all-zero
IBM floating-point representation as exactly `5.397605346934028e-79`.
Earlier v0.48/v0.48.1 code matched questionnaire responses strictly to
`0`, `1`, `2`, `3`, erroneously excluding many valid zero responses.

The v0.48.2 source uses **exact-equality** normalization of that decoder artifact
immediately after reading any public XPT table and **before** mapping questionnaire
codes. It preserves SAS missing values, refused/don't-know values, and legitimate
nonzero measurements, and is covered by targeted invented-byte and generated-fixture
tests. The feature coverage audit must be rerun to confirm actual PHQ-9 response
counts before interpreting any model output.

Both v0.48 and v0.48.1 later-cycle results were **previously inspected**.
The repaired experiment is a repeat exploratory sensitivity analysis, **NOT a fresh
independent evaluation**. All real data and aggregate results remain local outside
GitHub/Vercel; old historical NHANES mortality analysis stays blocked.
