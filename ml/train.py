"""Leakage-conscious baseline benchmark on *synthetic-only* example records.

Not a clinical model. Random train/val/test holdout is for demonstration only.
Real HUNT studies must define endpoint timing, censoring, linking and splits anew.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, roc_auc_score,
                             log_loss, precision_score, recall_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.schema import (CATEGORICAL_FEATURES, FEATURES, FEATURE_LABELS,
                       FEATURE_UNITS, NUMERIC_FEATURES, TARGET)


def verify_synthetic(df: pd.DataFrame) -> None:
    """Hard gate: no real/private record can be exported to public demo assets."""
    required = set(FEATURES + [TARGET, 'patient_id', 'data_origin'])
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f'Input is missing required columns: {sorted(missing)}')
    if not df['data_origin'].eq('SYNTHETIC').all() or not df['patient_id'].str.match(r'^SYN-\d{5,}$').all():
        raise ValueError('PROTECTION: only generated SYNTHETIC records may enter demo training/export.')
    if df['patient_id'].duplicated().any():
        raise ValueError('Duplicate patient IDs: do not mix observations across splits.')
    if not df[TARGET].isin([0, 1]).all() or df[TARGET].nunique() != 2:
        raise ValueError('Outcome must contain both binary event classes.')


CORE_FEATURES = [c for c in FEATURES if c not in ('activity_minutes_day', 'oral_health_problem')]
FEATURE_GROUPS = {'Clinical': CORE_FEATURES, 'Expanded': FEATURES}


def make_pipeline(estimator: Any, feature_names: list[str] | None = None) -> Pipeline:
    """Fit train-only imputation/encoding, explicit missingness indicators."""
    cols = FEATURES if feature_names is None else feature_names
    numeric_cols = [k for k in NUMERIC_FEATURES if k in cols]
    categoric_cols = [k for k in CATEGORICAL_FEATURES if k in cols]
    numeric = Pipeline([
        ('imputer', SimpleImputer(strategy='median', add_indicator=True)),
        ('scaler', StandardScaler()),
    ])
    category = Pipeline([
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False)),
    ])
    transform = ColumnTransformer([
        ('num', numeric, numeric_cols),
        ('cat', category, categoric_cols),
    ], sparse_threshold=0)
    return Pipeline([('preprocess', transform), ('classifier', estimator)])


def bootstrap_intervals(y: pd.Series | np.ndarray, pred: np.ndarray,
                        seed: int = 42, repeats: int = 250) -> dict:
    """Person-level percentile bootstrap of fixed held-out predictions.

    These intervals quantify only sampling variability for a fixed synthetic model;
    they do not include uncertainty due to model fitting, tuning, dataset shift.
    """
    yy = np.asarray(y).astype(int)
    pp = np.asarray(pred, dtype=float)
    rng = np.random.default_rng(seed)
    draws = {k: [] for k in ('roc_auc','average_precision','brier')}
    for _ in range(repeats):
        inds = rng.integers(0, len(yy), len(yy))
        if np.unique(yy[inds]).size < 2:
            continue
        for k, v in metrics(yy[inds], pp[inds]).items():
            draws[k].append(v)
    return {k: [round(float(np.quantile(v, .025)), 4),
                round(float(np.quantile(v, .975)), 4)] for k, v in draws.items() if v}


def decision_curve(y: pd.Series | np.ndarray, pred: np.ndarray) -> list[dict]:
    """Illustrative decision-curve net benefit vs treat-all/none, NOT policy thresholds."""
    yy = np.asarray(y).astype(int)
    pp = np.asarray(pred)
    prevalence = yy.mean()
    result = []
    for t in (.05, .10, .15, .20, .25, .30, .40, .50):
        positive = pp >= t
        nb = (np.mean(positive & (yy == 1))
              - np.mean(positive & (yy == 0)) * t / (1 - t))
        all_nb = prevalence - (1-prevalence)*t/(1-t)
        result.append({'threshold':round(t*100,0), 'model':round(float(nb),4),
                       'all':round(float(all_nb),4), 'none':0})
    return result


def split_data(df: pd.DataFrame, seed: int = 42):
    ids_dev, ids_test = train_test_split(
        np.arange(len(df)), test_size=.20, random_state=seed, stratify=df[TARGET])
    ids_train, ids_val = train_test_split(
        ids_dev, test_size=.25, random_state=seed, stratify=df.iloc[ids_dev][TARGET])
    assert not (set(ids_train) & set(ids_val) or set(ids_val) & set(ids_test)
                or set(ids_train) & set(ids_test)), 'Split leakage'
    return (df.iloc[ids_train].copy(), df.iloc[ids_val].copy(), df.iloc[ids_test].copy())


def metrics(y: pd.Series, p: np.ndarray) -> dict:
    return {'roc_auc': round(float(roc_auc_score(y, p)), 4),
            'average_precision': round(float(average_precision_score(y, p)), 4),
            'brier': round(float(brier_score_loss(y, p)), 4)}


def band(score: float) -> str:
    """Arbitrary illustrative grouping, not a clinically validated cutoff."""
    return 'Higher' if score >= .40 else 'Moderate' if score >= .20 else 'Lower'


def display_value(col: str, value: Any) -> str:
    if pd.isna(value):
        return 'Not measured'
    if col == 'sex':
        return str(value)
    if col in ('previous_fall', 'weight_loss', 'exhaustion', 'oral_health_problem'):
        return 'Yes' if float(value) == 1 else 'No'
    unit = FEATURE_UNITS.get(col, '')
    if col in ('gait_speed_ms', 'bmi'):
        v = f'{float(value):.2f}' if col == 'gait_speed_ms' else f'{float(value):.1f}'
    else:
        v = f'{float(value):.0f}' if float(value).is_integer() else f'{float(value):.1f}'
    return f'{v} {unit}'.strip()


def explain_example(model: Pipeline, record: pd.Series, reference: dict) -> list[dict]:
    """One-variable-at-a-time prediction differences versus synthetic median/mode.

    These contrasts are NOT SHAP, causal effects or independent contributions.
    Correlated predictors make these non-additive; no counterfactual claims.
    """
    original = pd.DataFrame([record[FEATURES].to_dict()])
    p = float(model.predict_proba(original)[0, 1])
    differences = []
    for key in FEATURES:
        if pd.isna(record[key]):
            continue
        candidate = original.copy()
        candidate[key] = reference[key]
        baseline = float(model.predict_proba(candidate)[0, 1])
        difference = (p - baseline) * 100
        differences.append({'key': key, 'name': FEATURE_LABELS[key],
                            'value': display_value(key, record[key]),
                            'delta_pp': round(difference, 1)})
    differences.sort(key=lambda x: abs(x['delta_pp']), reverse=True)
    return differences[:5]


def calibration_bins(y: pd.Series, p: np.ndarray) -> list[dict]:
    result = []
    for a, b in zip(np.linspace(0, 1, 9)[:-1], np.linspace(0, 1, 9)[1:]):
        mask = (p >= a) & (p < b if b < 1 else p <= b)
        if mask.sum():
            result.append({'predicted': round(float(p[mask].mean()), 3),
                           'observed': round(float(np.asarray(y)[mask].mean()), 3),
                           'count': int(mask.sum())})
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data/synthetic_cohort.csv')
    parser.add_argument('--output', default='web/public/data/demo.json')
    parser.add_argument('--artifact', default='artifacts/synthetic_model.joblib')
    parser.add_argument('--report', default='artifacts/experiment_report.json')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    df = pd.read_csv(args.input)
    verify_synthetic(df)
    train, validation, test = split_data(df, args.seed)

    # Compare feature availability and algorithm together, without using the test set.
    # Core = conventional clinical predictors; expanded = core + oral/wearable proxies.
    factories = {
        'Regularized logistic regression': lambda: LogisticRegression(max_iter=1600, C=.3),
        'Random forest': lambda: RandomForestClassifier(n_estimators=160, min_samples_leaf=12,
                                  max_features=.7, random_state=args.seed, n_jobs=-1),
        'Histogram gradient boosting': lambda: HistGradientBoostingClassifier(
                                  max_iter=120, max_leaf_nodes=15, l2_regularization=5.0,
                                  learning_rate=.06, random_state=args.seed),
    }
    fitted = {}
    results = []
    for group, columns in FEATURE_GROUPS.items():
        for name, factory in factories.items():
            model = make_pipeline(factory(), columns)
            model.fit(train[columns], train[TARGET])
            val_p = model.predict_proba(validation[columns])[:, 1]
            score = metrics(validation[TARGET], val_p)
            entry = {'name': f'{group} · {name}', 'family': name,
                     'featureGroup': group, 'nFeatures': len(columns), 'validation': score}
            results.append(entry)
            fitted[entry['name']] = model
            print(f'{entry["name"]}: ROC-AUC={score["roc_auc"]:.3f}; '
                  f'AP={score["average_precision"]:.3f}; Brier={score["brier"]:.3f}')

    # Lock winner using validation Brier only. No test-based tuning or reselection.
    best_entry = min(results, key=lambda e: (e['validation']['brier'], e['validation']['roc_auc']*-1))
    best_name = best_entry['name']
    cols = FEATURE_GROUPS[best_entry['featureGroup']]
    model = fitted[best_name]
    p_test = model.predict_proba(test[cols])[:, 1]
    test_results = metrics(test[TARGET], p_test)
    test_ci = bootstrap_intervals(test[TARGET], p_test, seed=args.seed)
    print(f'Selected {best_name}. TEST: {test_results}; bootstrap intervals {test_ci}')

    # Fixed comparator allows a proper paired core vs expanded model assessment.
    core_name = 'Clinical · Regularized logistic regression'
    core_model = fitted[core_name]
    core_p = core_model.predict_proba(test[CORE_FEATURES])[:, 1]
    core_result = metrics(test[TARGET], core_p)
    print(f'Clinical LR comparator TEST: {core_result}')

    sample = test.sample(n=min(450, len(test)), random_state=args.seed)
    importance = permutation_importance(model, sample[cols], sample[TARGET],
                                        n_repeats=3, random_state=args.seed,
                                        scoring='roc_auc', n_jobs=1)
    global_features = sorted([
        {'key': col, 'name': FEATURE_LABELS[col],
         'importance': round(float(imp), 4)}
        for col, imp in zip(cols, importance.importances_mean)],
        key=lambda item: item['importance'], reverse=True)[:8]

    reference = {}
    for key in NUMERIC_FEATURES:
        reference[key] = float(train[key].median())
    for key in CATEGORICAL_FEATURES:
        reference[key] = str(train[key].mode(dropna=True).iloc[0])
    samples = test.copy()
    samples['_probability'] = p_test
    selection = samples.sample(n=min(90, len(samples)), random_state=args.seed)
    patients = []
    for _, row in selection.iterrows():
        p = float(row['_probability'])
        values = [{'key': k, 'name': FEATURE_LABELS[k],
                   'value': display_value(k, row[k]),
                   'is_missing': bool(pd.isna(row[k]))} for k in FEATURES]
        # A local contrast changes one feature at a time, while every other input remains fixed.
        # Only fields used by the selected model can influence it.
        contributions = explain_example_with_columns(model, row, reference, cols)
        patients.append({'id': str(row['patient_id']), 'age': int(row['age']),
                         'sex': str(row['sex']), 'risk': round(p * 100, 1),
                         'band': band(p), 'features': values,
                         'explanations': contributions})
    patients.sort(key=lambda item: item['risk'], reverse=True)

    distribution = [{'name': k, 'count': int(sum(band(p) == k for p in p_test))}
                    for k in ('Lower','Moderate','Higher')]
    agegroup = pd.cut(test['age'], bins=[69,79,89,120], labels=['70–79','80–89','90+'])
    age_dist = [{'group': str(k), 'count': int(sum(agegroup == k)),
                 'meanRisk': round(float(np.mean(p_test[np.asarray(agegroup == k)]))*100,1)}
                for k in agegroup.cat.categories]
    subgroup = []
    for name, mask in [('Female', np.asarray(test.sex == 'Female')),
                       ('Male', np.asarray(test.sex == 'Male')),
                       ('70–79 years', np.asarray(test.age < 80)),
                       ('80–89 years', np.asarray((test.age >= 80) & (test.age < 90))),
                       ('90+ years', np.asarray(test.age >= 90))]:
        if mask.sum() == 0: continue
        local_y = test[TARGET].to_numpy()[mask]
        local_p = p_test[mask]
        subgroup.append({'name': name, 'n': int(mask.sum()),
                         'eventRate': round(float(local_y.mean()*100),1),
                         'auc': round(float(roc_auc_score(local_y,local_p)),3)
                           if np.unique(local_y).size > 1 else None,
                         'brier': round(float(brier_score_loss(local_y,local_p)),3)})

    coverage = [{'name': FEATURE_LABELS[col],
                 'percent': round(float(df[col].notna().mean()*100),1)}
                for col in ['gait_speed_ms','grip_strength_kg','moca_score',
                            'oral_health_problem','activity_minutes_day']]
    metadata = {
        'product':'FrailtyScope | Explainable Ageing & Health Intelligence',
        'dataOrigin':'SYNTHETIC', 'dataset':'Synthetic frailty demonstration cohort',
        'target':'Artificial fall event within 12 months',
        'warning':'Synthetic demonstration only. No HUNT participant data. '
                  'Artificial event mechanisms and simulated estimates are not clinically validated.',
        'explanationMethod':'One-feature response contrast against a synthetic training reference; '
                            'non-additive, non-causal, NOT SHAP.',
        'thresholds':'<20%, 20–39.9%, ≥40% are illustrative display bands, not clinical thresholds.',
        'validation':'Stratified 60/20/20 patient split (not temporal or external validation)',
        'uncertainty':'95% percentile bootstrap intervals conditional on a fixed model/synthetic test sample',
    }
    export = {
        'meta':metadata,
        'summary':{'records':int(len(df)), 'testSize':int(len(test)),
                   'artificialEventRate':round(float(df[TARGET].mean()*100),1),
                   'selectedModel':best_name, 'selectedFeatures':len(cols),
                   'featureGroup':best_entry['featureGroup'],
                   'test':test_results, 'testCI':test_ci,
                   'clinicalComparator':core_result},
        'comparisons':results,
        'riskDistribution':distribution, 'ageDistribution':age_dist,
        'globalFeatures':global_features,
        'calibration':calibration_bins(test[TARGET], p_test),
        'decisionCurve':decision_curve(test[TARGET], p_test),
        'subgroups':subgroup, 'coverage':coverage, 'patients':patients,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(export, indent=2, ensure_ascii=False)+'\n',encoding='utf-8')
    artifact = Path(args.artifact)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({'pipeline':model,'features':cols,'selected_model':best_name,
                 'synthetic_only':True},artifact)
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({'protocol':'synthetic prototype; not a clinical study',
                   'seed':args.seed,'split':{'train':len(train),'validation':len(validation),'test':len(test)},
                   'model_selection':'Minimum validation Brier, with ROC-AUC tie break',
                   'comparisons':results,'test':test_results,'intervals':test_ci,
                   'clinical_logistic_comparator':core_result}, indent=2)+'\n',encoding='utf-8')
    print(f'Saved synthetic PUBLIC dashboard data: {output}')
    print(f'Saved synthetic LOCAL model and report: {artifact}, {report}')


def explain_example_with_columns(model: Pipeline, record: pd.Series,
                                 reference: dict, columns: list[str]) -> list[dict]:
    """Non-additive perturbation, restricted to actual model inputs."""
    original = pd.DataFrame([record[columns].to_dict()])
    p = float(model.predict_proba(original)[0, 1])
    differences = []
    for key in columns:
        if pd.isna(record[key]):
            continue
        candidate = original.copy()
        candidate[key] = reference[key]
        baseline = float(model.predict_proba(candidate)[0, 1])
        differences.append({'key':key, 'name':FEATURE_LABELS[key],
                            'value':display_value(key,record[key]),
                            'delta_pp':round((p-baseline)*100,1)})
    differences.sort(key=lambda obj:abs(obj['delta_pp']),reverse=True)
    return differences[:5]


if __name__ == '__main__':
    main()
