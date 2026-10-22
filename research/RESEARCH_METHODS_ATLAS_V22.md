# FrailtyScope v0.22 — research-methods atlas, capabilities and gaps

**Purpose:** a source-controlled, task-first readiness and methods inventory for future NTNU/HUNT-like assignments. This is not a claim to have implemented every method below. It does not certify ethical access, clinical use, external validity, or an optimal algorithm.

## Non-negotiable sequence

1. **Approvals and intended purpose:** PI, data rights, lawful basis, ethics/REK and HUNT DAC if applicable; consent/withdrawal handling; permitted compute/storage, access restrictions, retention; written research question and decision context.
2. **Study definition (PICOTS):** population, prediction index time, target outcome, comparison, time horizon, setting, intended use; eligibility, source design and sampling frame; potential causal vs predictive objective (not interchangeable).
3. **Source/data contract:** exact file and processing fingerprints, dictionary, units, codebooks, versions, wave harmonization, duplicates, unrealistic values, linkage, sample flow; no labels or feature recoding by guesswork.
4. **Missingness/measurement:** distinguish structural skips, not applicable, no activity, refusal, unknown, assay detection limits, nonresponse, measurements after index; quantify mechanism hypotheses but never infer MAR/MNAR from correlations alone. Fit preprocessing exclusively on training partitions.
5. **Design route before model selection:** binary/continuous vs censored survival vs repeated-visit/multistate vs causal design; grouped/site/time sampling and clustering; leakage risks. Unsuited cases stop or use specialized engine.
6. **Analysis plan:** baselines, sample size and events, metrics and tolerances, nested tuning/selection, predeclared candidate model families, censoring/survey strategy, sensitivity experiments, training and evaluation boundary.
7. **Validation and utility:** paired proper scores, discrimination, calibration, uncertainty, subgroup heterogeneity, clinical consequences, external transportability; no confidence intervals from overlapping CV folds treated as independent samples.
8. **Reporting/decision:** cohort flow, predictions target/horizon, model card, transparent limitations, reproducible tables and figures, human review, independent ethical/clinical signoff; deploy only under explicitly separate authorization.

## Decision guide — no universally best method

| Data/problem | Preferred starting points / candidates | Correct validation considerations | Common failure to prevent | Implementation status |
|---|---|---|---|---|
| One-row binary risk with complete endpoint | Intercept-only and logistic reference; regularized logistic; trees, RF/boosting if justified | Development-only nested/group/time splits; Brier and log loss, calibration, AUROC/AP, decision curve if relevant | Imbalance manipulation outside folds; cutoff tuning on final evaluation | Tabular exploratory engine v0.10–v0.18 **implemented**, external clinical validation **not** |
| Continuous measurement | Mean/median + ridge/elastic net; suitable tree/boosting | RMSE/MAE; residuals, prediction intervals, subgroup/site splits | Treating skew/outliers without assessing target scale | Generic regression **implemented**, detailed intervals **gap** |
| Time-to-event, early censoring | Penalized Cox, flexible survival, competing-risk methods if relevant, survival forests/boosting as candidates | Time-dependent discrimination, IPCW Brier/calibration, censoring distribution, competing events, PH checks | Coding early-censored observations as negatives | Exploratory Cox v0.09 exists, **no production-grade generic survival engine** |
| Repeated participants / waves | Mixed models, GEE for longitudinal outcomes; landmark/joint/survival methods for dynamic risk | Participant/group separation, index chronology, visit leakage, informative dropout | Training on a person's visit and testing on another | Readiness routing v0.19 **implemented**; general longitudinal modeling **gap** |
| Multiple sites, families or devices | Mixed/fixed effects, stratified descriptive models; grouped/site held-out testing | GroupKFold, site-external, domain shift; avoid cluster leakage | Treating correlated records as independent | Gating **partial**, site-level evaluation **gap** |
| Irregular sensor/time series | Temporal aggregation inside training, time-aware models only if warranted | Forward-chaining, subject-held-out, sampling rate and device harmonization | Future windows or missing sensor periods leaking outcome | **Gap**, not claimed supported |
| Repeated NHANES-style survey | Design-based descriptive analyses, appropriate weights/strata/PSUs; sensitivity vs prediction target | Estimand, weighting, clustered uncertainty, wave consistency | Calling unweighted CV results representative/population-valid | **Gap** for design-valid uncertainty |
| Small data, few events | Simple shrinkage baseline; prespecified predictors; penalization | Bootstrap optimism/corrected calibration; reasonable parameter budget | High-capacity tuning or unstable subgroup claims | Partially addressed; event-aware sizing protocol **gap** |
| Large heterogeneous multimodal | Establish modality/timestamp contracts first; late fusion/multimodal models only if adequate sample | Patient/site/time held-out, label and modality availability audit | Data mixing, modality mismatch, shortcut predictors | **Future extension**, not in v0.22 |
| Missing questionnaire answers | Codebook-specific status categories, special codes, skip-routing, training-only imputation | Source-backed category checks and paired development comparisons | Treating structural skip or code 5 as numerical severity | NHANES PFQ v0.20–v0.21 **verified for this instrument only** |
| Class imbalance | Appropriate baseline, Brier/log loss/AP; training-fold class weighting/resampling if justified | Evaluate original prevalence, calibration and clinical consequences | Oversampling before split, accuracy-only claims | Basic metrics present; general recipes **to be tested** |
| Distribution shift / missing modalities | Shift checks, temporal and geographic validation, conditional updating where justified | Independent transport data, prespecified recalibration with proper evaluation | Repeated reusing inspected test cohort as external validation | **Gap**, readiness warnings exist |
| Causal/intervention effect | Explicit causal estimand, DAG, confounder design and appropriate causal methods | Negative controls, treatment timing, sensitivity and identifying assumptions | Treating feature importance as causal effect | **Separate specialized protocol required** |

## Frailty-specific choices that must not be overlooked

- **What is frailty?** Decide whether the outcome is Fried physical frailty phenotype, deficit-accumulation Frailty Index, Clinical Frailty Scale, disability/ADL limitation, transitions between states, or a different validated construct. These are **not interchangeable labels**. Document instrument wording, cut points, direction of scale, missing-component rules and measurement invariance across HUNT waves.
- **Baseline detection versus future prediction:** If the outcome is frailty *measured now*, predictors used to construct that frailty score may make the model tautological. For incident frailty, establish that baseline nonfrail status and future assessment times are known; separately handle intervening death and dropout.
- **Frailty trajectory:** Repeated scores require within-person methods, visit windows, observation-process assumptions, death as a competing event, and participant-level validation. A conventional shuffled binary CV does not solve this.
- **Measurement sources:** Self-report, examination, register linkage and wearable measures can disagree; assess device/instrument change, language, response routing, time windows and source-dependent selection.
- **Outcome communication:** A frailty risk score, an individual change in frailty, 5-year mortality risk and a clinically actionable frailty assessment answer *different questions*. Predeclare what matters to healthcare users before scoring.

## What a strong research result must show

- **Cohort flow** with every inclusion/exclusion reason and follow-up status, and how participant counts, visits, event counts and missingness were determined.
- **Data dictionary and lineage** specifying source, codebook, units, range, missingness classification, measurement date, transformations and evidence; distinction between observed and derived fields.
- **Comparison table** showing simple references and tuned alternatives under the same evaluation units; algorithms and preprocessing fitted inside each development fold; all tunable choices frozen before genuinely independent evaluation.
- **Calibration** with intercept/slope when estimable, reliability plots with appropriate bins and proper scores; distinguish average risk correctness from conditional calibration; no decision threshold optimized on test data.
- **Discrimination** using AUROC/AP and relevant performance at feasible thresholds; provide prevalence and operating-point limitations. Regression and survival use outcome-specific scores.
- **Clinical value** only for an actual decision context: net benefit/decision curves, harms, feasibility, burden and human oversight; statistical improvement alone is not clinical utility.
- **Uncertainty and robustness** using appropriate resampling unit (participant/site) and design-based inference where required; account for model selection and optimism; perturb instrument assumptions and assess missing-data sensitivity.
- **Equity** subgroup examination with adequate event/sample counts and privacy suppression, transparent limits and population-specific transportability. Avoid unstable rankings of tiny groups.
- **Reproducibility** environment lock, seed/code/data fingerprints, feature dictionary, protocol versions, split protocol, artifact checks, source-only publication, approved access, and auditable decisions.
- **Safe communication** description of prediction horizon, target population and intended use; avoid unsupported individual risk scores, clinical claims, confidence or causal interpretation.

## Reporting vs risk-of-bias vs privacy are distinct

- **TRIPOD+AI (2024)** is the modern reporting framework for development/evaluation of clinical prediction models. It helps structure research reporting; *not* a modeling recipe or quality seal: https://doi.org/10.1136/bmj-2023-078378
- **PROBAST+AI (2025)** is a separate structured judgment about quality, risk of bias and applicability: https://doi.org/10.1136/bmj-2024-082505
- For observational and routinely collected data consider STROBE/RECORD when appropriate, and additional cluster/survival/causal reporting where appropriate. These cannot replace source-specific approvals.
- **HUNT access/REK/DAC:** The project PI/institution must satisfy actual HUNT requirements, obtain approved scope and agreements, and follow study-specific publication review and data-retention rules: https://www.ntnu.edu/hunt/data/ . This source-only NHANES development work does **not** mean HUNT approval.

## What is implemented at v0.22 vs still required

| Capability | Evidence and boundary | Next milestone |
|---|---|---|
| Generic tabular case loading, feature guards, fit/tune/evaluate | v0.10–v0.16; exploratory development | Harden for new dataset-specific contract, model reproducibility tests |
| Missing indicators, nested selection, reliability/calibration diagnostics | v0.14–v0.18; not independent evaluation | Cross-case test and prespecified selection policy |
| Data readiness and routing | v0.19 source-aware intake, no fitting | Extend beyond cohort splits and verify with synthetic longitudinal/site fixtures |
| Original survey PFQ semantics | v0.20 reconciliation and v0.21 encoding; **NHANES-specific** | Generic codebook/routing schema, not copied questionnaire rules |
| Mortality label provenance and selection flow | Local read-only audits, internally reconciled 2011–2012 only | Create private signed evidence record; preserve follow-up perturbation limitation |
| Source-controlled scientific evidence checklist | v0.22 document/register with optional local aggregate metadata validation | Real-assignment preflight completed by PI/domain experts |
| Survey-design inference, survival/landmark/competing risk, grouped/time evaluation | Experimental or readiness routing only | Separate tested implementations before use |
| Clinical use, regulatory approval, HUNT access, unseen-cohort performance | **Not established** | Requires approvals, new data and suitable independent validation |

**Current NHANES honesty rule:** 2013–2014 was previously inspected in historical work; v0.13–v0.21 development observations overlap across CV repeats. The 2019 public-use mortality follow-up may be synthetically perturbed. Do not advertise fresh independent external validation, clinical risk prediction, or source category transfer to HUNT.

## Definition of readiness for a real assignment

The system is ready for a *particular* dataset only after an authorized study team can: (a) demonstrate lawful data access and a written PICOTS/outcome/measurement protocol; (b) reconcile participant/visit IDs, record timing, eligibility and missingness with source documentation; (c) choose a compatible resampling and outcome route including censoring and survey effects; (d) predeclare a validation plan and clinically relevant metrics; (e) execute the tested specialized engine within authorized computing; and (f) provide an independent evaluation and appropriately limited presentation of results. **v0.22 alone does not pass this test.**

Research software readiness is not automatic clinical or regulatory deployment authorization. Keep one independent evaluation set genuinely uninspected for future assignments, and never reinterpret the previously inspected NHANES cycle as such a set.
