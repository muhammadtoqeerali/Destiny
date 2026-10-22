# FrailtyScope v0.16: Joint model-family and missing-data preprocessing selection

## Aim

Select a **model family + preprocessing policy + hyperparameters** together, rather
than assuming the best missingness strategy for a fixed logistic model transfers
to a tree-boosting model. Comparisons occur on the **development cohort only**.

## Study design

- Inputs: a local case manifest, a compatible v0.13 **protocol configuration** (no earlier training required), and a v0.16 list of preprocessing definitions.
- Pairs: five existing model families × the **reference** or **numeric missingness-indicator** policy, subject to each manifest's allowed families.
- Each outer fold: screen every pair with 2 inner-CV Optuna trials; promote the 3 strongest pairs; refine promoted pairs with 8 trials; prefer lower inner-CV loss, with an a priori 0.001 Brier practical tie margin favoring simpler configurations.
- Independently tune the logistic-reference regularization using the explicitly declared baseline regularization grid on those same outer-development training cases.
- Compare joint selection with the tuned logistic-reference using identical outer assessment folds. Cross-validation imputers, scalers and encoders are refitted **inside each training fold**.
- On full development only: repeat the selection and fit the final chosen pipeline, save its model locally, and derive an exploratory threshold from development out-of-fold scores.
- Never fit, score, search or promote using later-cycle evaluation observations.

## Results and interpretation

The run writes **only local** artifacts under
`artifacts/cases/<case_id>/joint_selection_v16/<protocol-hash>/`:

- `joint_selection.json`: model-family/policy frequencies, fold results, nested-comparison loss, final selected recipe and explicit scientific limitations.
- `winner_development_only.joblib`: fitted final-development pipeline, **never committed**.

The *nested CV comparison estimates the algorithm-selection procedure,* not final
model external performance. Earlier v0.13–v0.15 NHANES analyses motivated these
candidates on the same development sample. Thus the present comparison remains
**exploratory reuse**, not fresh independent validation; repeated outer CV folds
contain overlapping participants and are not independent confidence intervals.
The 2013–2014 cycle has been examined previously and stays untouched here.

This is for research, not clinical risk reporting. Neither a good Brier score nor
threshold-selection arithmetic establishes clinical operating utility.

## Running locally

1. `PYTHONPATH=. .venv/bin/python -m ml.case_joint_selection_v16 --plan`
2. After review: `PYTHONPATH=. .venv/bin/python -m ml.case_joint_selection_v16 --run`

`--plan` reads local aggregate design contracts without model fitting. `--run`
fits diagnostic and final-development models **only on the workstation**.
No model inference, fitting, train-test evaluation, or NHANES data access is
performed by the release author's environment.

For a new assignment, create a case manifest plus a compatible v0.13 strategy
configuration; **no prior model fitting or ablation result is required**.
Do not rename an old cohort or assume
binary classification is suitable for censored/longitudinal outcomes.
