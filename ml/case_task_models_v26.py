"""FrailtyScope v0.26 -- synthetic-only task-aware model comparison.

No CSV/XPT reading, model loading, private data, holdout inspection, export,
or real research fitting in the CLI. evaluate_synthetic_candidates accepts ONLY
invented in-memory fixtures; its explicit flag is not a security sandbox.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

from ml.case_foldsafe_v25 import (build_preprocessor, expected_columns,
                                 local_file, validate_partition, validate_recipe)

SCHEMA = 'FRAILTYSCOPE_TASK_MODEL_PROTOCOL_V26'
REPORT_SCHEMA = 'FRAILTYSCOPE_PRIVATE_TASK_MODEL_REVIEW_V26'
SUPPORTED = {'classification', 'regression'}
SPECIALIZED = {'survival', 'longitudinal'}
METRICS = {
    'classification': ('brier', 'log_loss', 'roc_auc', 'average_precision'),
    'regression': ('mae', 'rmse', 'r2'),
}
DIRECTION = {'brier': 'min', 'log_loss': 'min', 'roc_auc': 'max',
             'average_precision': 'max', 'mae': 'min', 'rmse': 'min', 'r2': 'max'}
CANDIDATES = {
    'classification': {'dummy_prior', 'logistic', 'random_forest', 'hist_gradient_boosting'},
    'regression': {'dummy_mean', 'ridge', 'random_forest', 'hist_gradient_boosting'},
}
PARAMS = {
    'dummy_prior': {}, 'dummy_mean': {},
    'logistic': {'C': (0.001, 1000.0)},
    'ridge': {'alpha': (0.0001, 1000.0)},
    'random_forest': {'n_estimators': (5, 200), 'max_depth': (1, 20),
                      'min_samples_leaf': (1, 30)},
    'hist_gradient_boosting': {'max_iter': (10, 200),
                               'learning_rate': (0.005, 0.5),
                               'max_leaf_nodes': (2, 31)},
}
INT_PARAMS = {'n_estimators', 'max_depth', 'min_samples_leaf', 'max_iter', 'max_leaf_nodes'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def _valid_params(spec):
    name = spec.get('name')
    params = spec.get('params')
    require(name in PARAMS and isinstance(params, dict) and
            set(params) == set(PARAMS[name]), 'Unsupported or incomplete model parameters')
    for key, bounds in PARAMS[name].items():
        value = params[key]
        require(type(value) in (int, float) and math.isfinite(value) and
                bounds[0] <= value <= bounds[1] and
                (key not in INT_PARAMS or type(value) is int),
                'Unsafe or invalid model parameter: '+key)


def validate_design(cfg, recipe, manifest=None):
    require(isinstance(cfg, dict) and cfg.get('schema') == SCHEMA,
            'Unrecognized task-model schema')
    require(cfg.get('case_id') == recipe.get('case_id'), 'Case identity mismatch')
    require(cfg.get('holdout_history') == recipe.get('holdout_history') and
            cfg.get('prior_exploration') == recipe.get('prior_exploration') and
            cfg.get('prediction_index_status') == recipe.get('prediction_index_status'),
            'Prior evaluation/timing history may not be reset')
    require(cfg.get('split_policy') == recipe.get('split_review'),
            'Task model split must match protected preprocessing boundary')
    require(cfg.get('related_v25_protocol') and cfg.get('related_private_v25_review'),
            'Source and private documentary lineage required')
    require(cfg.get('scope') == 'synthetic_only_blueprint' and
            cfg.get('real_data_execution_permitted') is False and
            cfg.get('model_fitting_permitted') is False and
            cfg.get('holdout_scoring_permitted') is False and
            cfg.get('clinical_use_permitted') is False and
            cfg.get('public_export_permitted') is False,
            'Model selection blueprint cannot authorize real research fitting')
    task = cfg.get('task')
    require(task in SUPPORTED | SPECIALIZED, 'Unknown outcome task')
    if manifest is not None:
        require(manifest.get('case_id') == cfg['case_id'] and
                manifest.get('task') == task, 'Study manifest task mismatch')
    require(type(cfg.get('random_seed')) is int and 0 <= cfg['random_seed'] <= 2**32-1,
            'Deterministic random seed required')
    require(type(cfg.get('n_splits')) is int and 2 <= cfg['n_splits'] <= 5,
            'Bounded development CV folds required')
    require(cfg.get('selection_rule') == 'development_cv_only',
            'CV comparison is exploratory, never independent validation')
    require(cfg.get('test_set_role') == 'not_accessed',
            'Inspected evaluation data cannot be reused as fresh holdout')
    specs = cfg.get('candidates')
    require(isinstance(specs, list) and len(specs) <= 8,
            'Bounded prespecified candidate list required')
    if task in SPECIALIZED:
        require(specs == [] and cfg.get('primary_metric') is None,
                'Survival/longitudinal engines require a specialized protocol')
    else:
        require(2 <= len(specs) <= 8 and
                cfg.get('primary_metric') in METRICS[task],
                'Missing valid candidate set or task-specific selection metric')
        names = []
        for spec in specs:
            require(isinstance(spec, dict) and set(spec) == {'name', 'params'} and
                    spec['name'] in CANDIDATES[task], 'Candidate not supported for task')
            _valid_params(spec)
            names.append(spec['name'])
        require(len(names) == len(set(names)), 'Duplicate model families not permitted in v0.26')
        require(('dummy_prior' if task == 'classification' else 'dummy_mean') in names,
                'Require trivial baseline to measure meaningful improvement')
    return cfg


def make_plan(cfg):
    task = cfg['task']
    blocked = 'BLOCKED_FOR_NEW_ANALYSIS' if task in SUPPORTED else 'SPECIALIZED_ENGINE_REQUIRED'
    return {'schema': REPORT_SCHEMA, 'case_id': cfg['case_id'],
            'config_sha256': digest(cfg), 'route': blocked,
            'task': task, 'supported_for_synthetic_cv': task in SUPPORTED,
            'index_status': cfg['prediction_index_status'],
            'holdout_history': cfg['holdout_history'],
            'split_policy': cfg['split_policy'], 'n_splits': cfg['n_splits'],
            'candidate_names': [c['name'] for c in cfg['candidates']],
            'primary_metric': cfg['primary_metric'], 'synthetic_only': True,
            'no_participant_tables_opened': True, 'no_models_fitted': True,
            'no_predictions_generated': True, 'no_holdout_targets_accessed': True,
            'public_export': False,
            'limitations': [
                'Development CV is model selection, not an untouched test-set estimate.',
                'Previously inspected NHANES later cycle is not fresh independent validation.',
                'Incomplete source mappings and provisional index still prohibit real-data execution.',
                'Survival and repeated-visit targets require specialized censoring/time-aware validation.',
                'No survey-design weighted estimands or clinical/transportability claims.'
            ]}


def _estimator(task, spec, seed):
    name, params = spec['name'], spec['params']
    if name == 'dummy_prior':
        from sklearn.dummy import DummyClassifier
        return DummyClassifier(strategy='prior')
    if name == 'dummy_mean':
        from sklearn.dummy import DummyRegressor
        return DummyRegressor(strategy='mean')
    if name == 'logistic':
        from sklearn.linear_model import LogisticRegression
        return LogisticRegression(**params, max_iter=1200, random_state=seed)
    if name == 'ridge':
        from sklearn.linear_model import Ridge
        return Ridge(**params)
    if name == 'random_forest':
        if task == 'classification':
            from sklearn.ensemble import RandomForestClassifier
            return RandomForestClassifier(**params, random_state=seed, n_jobs=1)
        from sklearn.ensemble import RandomForestRegressor
        return RandomForestRegressor(**params, random_state=seed, n_jobs=1)
    if name == 'hist_gradient_boosting':
        if task == 'classification':
            from sklearn.ensemble import HistGradientBoostingClassifier
            return HistGradientBoostingClassifier(**params, random_state=seed)
        from sklearn.ensemble import HistGradientBoostingRegressor
        return HistGradientBoostingRegressor(**params, random_state=seed)
    raise ValueError('Unknown estimator family')


def _validate_outcome(y, task, count):
    import numpy as np
    require(not isinstance(y, str), 'Outcome must be an array')
    values = np.asarray(y)
    require(values.ndim == 1 and len(values) == count and
            values.dtype.kind in 'iuf' and np.isfinite(values).all(),
            'Outcome must be a finite, one-dimensional numeric array')
    if task == 'classification':
        require(set(values.tolist()) == {0, 1}, 'Binary 0/1 target required')
        values = values.astype(int)
    else:
        values = values.astype(float)
        require(len(set(values.tolist())) >= 3, 'Regression target requires variation')
    return values


def _fold_indices(cfg, n, y, *, row_ids, groups, timestamps):
    """Build full fold plan and validate ALL boundaries before fitting any model."""
    import numpy as np
    import pandas as pd
    from sklearn.model_selection import GroupKFold, TimeSeriesSplit

    k = cfg['n_splits']
    policy = cfg['split_policy']
    require(row_ids is not None and len(row_ids) == n and
            len(set(row_ids)) == n and not any(pd.isna(x) for x in row_ids),
            'Unique nonmissing row identifiers required outside predictors')
    if 'person' in policy:
        require(groups is not None and len(groups) == n and
                not any(pd.isna(x) for x in groups),
                'Person grouping metadata required outside features')
    if 'time' in policy:
        require(timestamps is not None and len(timestamps) == n,
                'Time metadata required outside features')
        clock = pd.to_datetime(list(timestamps), utc=True, errors='coerce')
        require(not clock.isna().any(), 'Invalid visit/index timestamps')
        unique_times = np.sort(clock.unique())
        require(len(unique_times) >= k+2, 'Not enough distinct times for forward CV')
        ordered_times = TimeSeriesSplit(n_splits=k).split(unique_times)
        folds = [(np.flatnonzero(clock.isin(unique_times[a])),
                  np.flatnonzero(clock.isin(unique_times[b]))) for a, b in ordered_times]
    else:
        require(len(set(groups)) >= k, 'Insufficient distinct groups for CV')
        folds = list(GroupKFold(n_splits=k).split(np.zeros(n), y, groups=groups))

    validated = []
    for tr, va in folds:
        require(len(tr) >= 3 and len(va) >= 2, 'Fold too small for interpretable comparison')
        validate_partition([row_ids[i] for i in tr], [row_ids[i] for i in va],
             policy=policy,
             train_groups=[groups[i] for i in tr] if groups is not None else None,
             valid_groups=[groups[i] for i in va] if groups is not None else None,
             train_time=[timestamps[i] for i in tr] if timestamps is not None else None,
             valid_time=[timestamps[i] for i in va] if timestamps is not None else None)
        if cfg['task'] == 'classification':
            require(set(y[tr]) == {0, 1} and set(y[va]) == {0, 1},
                    'Every training and validation fold needs both outcome classes')
        else:
            require(len(set(y[tr].tolist())) >= 2 and len(set(y[va].tolist())) >= 2,
                    'Every regression fold needs varying outcomes')
        validated.append((tr, va))
    return validated


def _score(task, truth, predictor, probability=None):
    import numpy as np
    from sklearn.metrics import (average_precision_score, brier_score_loss,
       log_loss, roc_auc_score, mean_absolute_error, mean_squared_error, r2_score)
    if task == 'classification':
        require(probability is not None and np.isfinite(probability).all() and
                ((probability >= 0) & (probability <= 1)).all(),
                'Invalid probability estimates')
        return {'brier': float(brier_score_loss(truth, probability)),
                'log_loss': float(log_loss(truth, np.clip(probability, 1e-15, 1-1e-15), labels=[0,1])),
                'roc_auc': float(roc_auc_score(truth, probability)),
                'average_precision': float(average_precision_score(truth, probability))}
    return {'mae': float(mean_absolute_error(truth, predictor)),
            'rmse': float(np.sqrt(mean_squared_error(truth, predictor))),
            'r2': float(r2_score(truth, predictor))}


def evaluate_synthetic_candidates(cfg, recipe, frame, y, *, row_ids,
                                   groups=None, timestamps=None, synthetic_fixture=False):
    """Explore prespecified candidates under identical, leakage-guarded CV folds.

    Does not save estimators, predictions, samples or reports. Requires invented
    synthetic fixtures only; never call this method with real research data.
    """
    require(synthetic_fixture is True, 'Real research model fitting not authorized')
    require(cfg['task'] in SUPPORTED, 'Specialized survival/longitudinal engine required')
    validate_design(cfg, recipe)
    import numpy as np
    import pandas as pd
    from sklearn.pipeline import Pipeline
    import sklearn
    require(isinstance(frame, pd.DataFrame) and frame.columns.is_unique and
            len(frame) > 0 and set(frame.columns) == set(expected_columns(recipe)),
            'Feature matrix must contain exactly authorized predictors and statuses')
    truth = _validate_outcome(y, cfg['task'], len(frame))
    folds = _fold_indices(cfg, len(frame), truth, row_ids=row_ids, groups=groups,
                          timestamps=timestamps)
    results = []
    for candidate in cfg['candidates']:
        metric_rows = []
        for train_idx, valid_idx in folds:
            pipeline = Pipeline([
                ('preprocessing', build_preprocessor(recipe, synthetic_fixture=True)),
                ('estimator', _estimator(cfg['task'], candidate, cfg['random_seed']))])
            pipeline.fit(frame.iloc[train_idx], truth[train_idx])
            if cfg['task'] == 'classification':
                scores = pipeline.predict_proba(frame.iloc[valid_idx])[:, 1]
                measure = _score('classification', truth[valid_idx], None, scores)
            else:
                estimates = pipeline.predict(frame.iloc[valid_idx])
                measure = _score('regression', truth[valid_idx], estimates)
            metric_rows.append(measure)
        mean_scores = {metric: float(np.mean([row[metric] for row in metric_rows]))
                       for metric in METRICS[cfg['task']]}
        require(all(math.isfinite(v) for v in mean_scores.values()),
                'Nonfinite fold metrics')
        results.append({'name': candidate['name'], 'mean_metrics': mean_scores,
                        'folds': len(metric_rows)})
    direction = DIRECTION[cfg['primary_metric']]
    results.sort(key=lambda row: ((row['mean_metrics'][cfg['primary_metric']]
                                   if direction == 'min' else
                                   -row['mean_metrics'][cfg['primary_metric']]), row['name']))
    return {'schema': 'FRAILTYSCOPE_SYNTHETIC_DEV_CV_V26',
            'task': cfg['task'], 'config_sha256': digest(cfg),
            'n_splits': len(folds), 'n_synthetic_rows': len(frame),
            'n_fits': len(folds)*len(results),
            'selection_metric': cfg['primary_metric'],
            'candidate_rankings': results,
            'top_development_candidate': results[0]['name'],
            'environment': {'python': sys.version.split()[0], 'sklearn': sklearn.__version__},
            'development_only': True, 'independent_validation': False,
            'models_saved': False, 'participant_predictions_exported': False,
            'clinical_use_permitted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    select = parser.add_mutually_exclusive_group(required=True)
    select.add_argument('--plan', action='store_true')
    select.add_argument('--audit', action='store_true')
    parser.add_argument('--project', default='.')
    parser.add_argument('--config', default='research/cases/nhanes_task_models_v26.json')
    args = parser.parse_args()
    root = Path(args.project).resolve()
    cfg = json.loads(local_file(root, args.config, 'research').read_text())
    recipe = json.loads(local_file(root, cfg['related_v25_protocol'], 'research').read_text())
    from ml.case_dictionary_timing_v23 import validate_protocol as check_v23
    from ml.case_governance_v22 import validate_protocol as check_v22
    from ml.case_harmonization_v24 import validate_protocol as check_v24
    v23 = json.loads(local_file(root, recipe['related_v23_protocol'], 'research').read_text())
    v24 = json.loads(local_file(root, recipe['related_v24_protocol'], 'research').read_text())
    manifest = json.loads(local_file(root, v23['case_manifest'], 'research').read_text())
    v22 = json.loads(local_file(root, v23['related_v22_protocol'], 'research').read_text())
    check_v22(v22);check_v23(v23,manifest,v22);check_v24(v24,v23)
    validate_recipe(recipe,v23,v24)
    validate_design(cfg,recipe,manifest)
    report=make_plan(cfg)
    if args.audit:
        parent_path=local_file(root,cfg['related_private_v25_review'],'artifacts')
        require(parent_path.suffix == '.json' and parent_path.stat().st_size < 250000,
                'Unsafe private parent report metadata')
        parent=json.loads(parent_path.read_text())
        require(parent.get('schema')=='FRAILTYSCOPE_PRIVATE_FOLDSAFE_PLAN_V25' and
                parent.get('case_id')==cfg['case_id'] and
                parent.get('config_sha256') == digest(recipe) and
                parent.get('v24_private_metadata_verified') is True and
                parent.get('route')=='BLOCKED_FOR_NEW_ANALYSIS' and
                parent.get('no_participant_tables_opened') is True and
                parent.get('no_models_fitted') is True and
                parent.get('no_holdout_targets_accessed') is True and
                parent.get('public_export') is False,
                'Prior private metadata review is invalid')
        report['v25_private_metadata_verified']=True
    print('V26 TASK MODELING PLAN:',json.dumps({key: report[key] for key in (
        'case_id','route','task','supported_for_synthetic_cv','index_status',
        'holdout_history','split_policy','n_splits','candidate_names','primary_metric')},indent=2))
    if args.audit:
        target=(root/'artifacts/cases'/cfg['case_id']/'task_models_v26'/
                digest(cfg)[:12]/'task_model_review.json').resolve()
        require(target.is_relative_to((root/'artifacts/cases').resolve())
                and not target.exists(), 'Immutable private v0.26 review exists')
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x') as stream:
            json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
        print('PRIVATE IMMUTABLE METADATA REVIEW:',target)
    else:
        print('PLAN ONLY. No local aggregate reports or participant records opened.')
    print('No research fits, predictions, labels, held-out outcomes or models accessed.')

if __name__=='__main__':
    main()
