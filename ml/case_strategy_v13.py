"""FrailtyScope v0.13: local-only, development-only model-selection protocol.

The file has no import-time fitting. Model search is explicit (--search) and always
runs on the researcher's workstation. All participant data and fitted models remain
under ignored data/ and artifacts/. Never publish local reports or model binaries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from collections import Counter

SCHEMA = 'FRAILTYSCOPE_CASE_STRATEGY_V13'
FAMILIES = ('logistic', 'ridge', 'hist_boost', 'random_forest', 'xgboost', 'catboost')
COMPLEXITY = {'logistic': 0, 'ridge': 0, 'hist_boost': 1,
              'random_forest': 2, 'catboost': 3, 'xgboost': 4}
METRICS = {'classification': {'brier', 'roc_auc', 'average_precision'},
           'regression': {'rmse', 'mae'}}
DEFAULT_MARGIN = {'brier': 0.001, 'roc_auc': 0.005, 'average_precision': 0.005,
                  'rmse': 0.0, 'mae': 0.0}


def require(ok, why):
    if not ok:
        raise ValueError(why)


def within_project(project: Path, relative: str, base: str) -> Path:
    require(isinstance(relative, str) and bool(relative), 'Required relative file path')
    root = (project / base).resolve()
    path = (project / relative).resolve()
    require(path.is_relative_to(root), f'Path must remain inside {base}/')
    require(path.is_file(), f'Required file is missing: {relative}')
    return path


def manifest_hash(config: dict) -> str:
    blob = json.dumps(config, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()


def validate_protocol(protocol: dict, manifest: dict) -> dict:
    from ml.case_engine_v10 import validate_manifest
    validate_manifest(manifest)
    require(isinstance(protocol, dict) and protocol.get('schema') == SCHEMA,
            'Invalid v0.13 strategy protocol')
    require(protocol.get('case_id') == manifest['case_id'], 'Mismatched case ID')
    task = manifest['task']
    metric = protocol.get('primary_metric')
    require(metric in METRICS[task], 'Primary metric incompatible with task')
    families = protocol.get('candidates')
    require(isinstance(families, list) and 2 <= len(families) <= 5,
            'Declare 2-5 non-dummy model families')
    require(len(set(families)) == len(families), 'Duplicate model family')
    require(all(m in manifest['models'] and m in FAMILIES and m != 'dummy'
                for m in families), 'Candidate not permitted by case manifest')
    if task == 'classification':
        require('ridge' not in families, 'Ridge belongs to regression')
    else:
        require('logistic' not in families, 'Logistic belongs to classification')
    for key, lo, hi in [('outer_folds', 2, 5), ('inner_folds', 2, 5),
                        ('screen_trials', 1, 12), ('refine_trials', 2, 40),
                        ('top_k', 1, 3)]:
        value = protocol.get(key)
        require(type(value) is int and lo <= value <= hi, f'Invalid {key}')
    require(protocol['refine_trials'] >= protocol['screen_trials'],
            'Refinement budget must not be smaller than screening budget')
    require(protocol['top_k'] < len(families), 'Promotion must select fewer than all candidates')
    margin = protocol.get('practical_tie_margin', DEFAULT_MARGIN[metric])
    require(type(margin) in (int, float) and math.isfinite(margin) and 0 <= margin <= .1,
            'Invalid practical tie margin')
    group = protocol.get('group_column')
    if group is not None:
        require(isinstance(group, str) and group and
                group not in manifest['features']['numeric'] + manifest['features']['categorical'] and
                group != manifest['target'], 'Group column cannot be a predictor or outcome')
    require(protocol.get('time_column') is None,
            'Longitudinal/time-varying inputs require an explicit landmark-and-time-split protocol;'
            ' v0.13 will not silently apply shuffled CV')
    require(protocol.get('holdout_status') in ('previously_inspected', 'locked_new'),
            'Declare holdout inspection status')
    return protocol


def select_from_scores(records: list[dict], metric: str, margin: float) -> dict:
    """Predeclared practical-equivalence rule: minimum loss, then simpler family.

    Margins are in objective loss units; never inspect evaluation outcomes here.
    This is a preference rule, NOT a statistical equivalence test.
    """
    require(metric in set.union(*METRICS.values()), 'Unknown metric')
    require(records and all('family' in r and 'loss' in r for r in records),
            'Missing candidate evidence')
    require(all(math.isfinite(float(r['loss'])) and r['family'] in COMPLEXITY
                for r in records), 'Nonfinite or unsupported candidate evidence')
    require(math.isfinite(margin) and margin >= 0, 'Invalid margin')
    best = min(float(r['loss']) for r in records)
    eligible = [r for r in records if float(r['loss']) <= best + margin + 1e-12]
    chosen = min(eligible, key=lambda r: (COMPLEXITY[r['family']], r['loss'], r['family']))
    return {'family': chosen['family'], 'loss': round(float(chosen['loss']), 8),
            'best_loss': round(best, 8), 'practical_tie_margin': margin,
            'considered_equivalent': [r['family'] for r in eligible],
            'reason': 'Best development CV loss, with a fixed practical margin favoring simpler models; not a significance test'}


def partition_contract(frame, y, development, evaluation, protocol: dict, manifest: dict):
    """Pure audit of group overlap, repeated visits and minimum outcome support."""
    import numpy as np
    development = np.asarray(development, dtype=int)
    evaluation = np.asarray(evaluation, dtype=int)
    require(len(set(development) & set(evaluation)) == 0, 'Development/evaluation overlap')
    require(len(development) >= 40 and len(evaluation) >= 15, 'Insufficient partition sizes')
    entity = manifest['id_column']
    require(entity in frame and frame[entity].notna().all(), 'Invalid person ID field')
    if frame[entity].duplicated().any():
        raise ValueError('Repeated person records detected: build a longitudinal landmark table '
                         'with verified index time, outcome horizon and group/time split before training')
    column = protocol.get('group_column')
    groups = None
    if column:
        require(column in frame and frame[column].notna().all(), 'Missing group information')
        groups = frame[column]
        a = set(groups.iloc[development])
        b = set(groups.iloc[evaluation])
        require(not a.intersection(b), 'Group/site leakage across development and evaluation')
        require(len(a) >= protocol['outer_folds'] and len(a) >= protocol['inner_folds'],
                'Not enough distinct development groups for CV')
    require(frame[entity].iloc[development].nunique() == len(development), 'Repeated development IDs')
    labels = y.iloc[development]
    if manifest['task'] == 'classification':
        counts = labels.value_counts()
        require(len(counts) == 2 and counts.min() >= 2 * protocol['inner_folds'],
                'Too few outcome events for inner CV')
    return {'development_n': int(len(development)),
            'evaluation_n': int(len(evaluation)),
            'groups_in_development': int(groups.iloc[development].nunique()) if groups is not None else None,
            'classification_events_in_development': int((labels == 1).sum())
                if manifest['task'] == 'classification' else None}



def development_profile(frame, y, development, manifest: dict) -> dict:
    """Profile DEVELOPMENT observations only; aggregate counts, no respondent rows."""
    import numpy as np
    indices = np.asarray(development, dtype=int)
    d = frame.iloc[indices]
    predictors = manifest['features']['numeric'] + manifest['features']['categorical']
    missing = [{'feature': col, 'missing_percent': round(float(d[col].isna().mean())*100, 2)}
               for col in predictors]
    missing.sort(key=lambda z: -z['missing_percent'])
    task = manifest['task']
    events = int((y.iloc[indices] == 1).sum()) if task == 'classification' else None
    prevalence = (round(float(events/len(indices)), 5) if events is not None else None)
    notes = []
    if any(z['missing_percent'] >= 25 for z in missing):
        notes.append('High missingness: compare native missing-value handling and missing-indicator ablations; fit imputers inside folds')
    if prevalence is not None and prevalence < .1:
        notes.append('Low event prevalence: report average precision, PR curves and calibration alongside ROC-AUC')
    if len(indices) < 10000 and len(predictors) <= 500:
        notes.append('Small tabular regime: an OPTIONAL local TabPFN experiment may be informative once model terms and hardware permit')
    notes.append('No model family is guaranteed to win; primary metric and selection rule must be fixed before search')
    return {'development_n': int(len(d)), 'predictor_count':len(predictors),
            'event_count': events, 'event_prevalence': prevalence,
            'missingness_percent_development': missing, 'design_recommendations': notes}

def fold_indices(y, folds: int, seed: int, task: str, groups=None):
    """Yield position-indexed train/validation splits. No fitting performed."""
    import numpy as np
    from sklearn.model_selection import KFold, StratifiedKFold, GroupKFold, StratifiedGroupKFold
    yy = np.asarray(y)
    if groups is None:
        splitter = (StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
                    if task == 'classification'
                    else KFold(n_splits=folds, shuffle=True, random_state=seed))
        iterator = splitter.split(np.zeros(len(yy)), yy if task == 'classification' else None)
    else:
        gg = np.asarray(groups)
        require(len(gg) == len(yy), 'Group vector length mismatch')
        require(len(set(gg)) >= folds, 'Insufficient groups')
        splitter = (StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed)
                    if task == 'classification' else GroupKFold(n_splits=folds))
        iterator = splitter.split(np.zeros(len(yy)), yy, gg)
    for train, valid in iterator:
        require(len(train) and len(valid), 'Empty cross-validation partition')
        require(not set(train).intersection(valid), 'Fold overlap')
        if groups is not None:
            require(not set(gg[train]).intersection(gg[valid]), 'Group crossed folds')
        if task == 'classification':
            require(len(set(yy[train])) == 2 and len(set(yy[valid])) == 2,
                    'One-class CV fold; reduce folds or change design')
        yield train, valid


def primary_loss(y, predictions, task: str, metric: str) -> float:
    import numpy as np
    from sklearn.metrics import (brier_score_loss, roc_auc_score,
                                 average_precision_score, mean_squared_error, mean_absolute_error)
    if task == 'classification':
        return (float(brier_score_loss(y, predictions)) if metric == 'brier' else
                1.0 - float(roc_auc_score(y, predictions)) if metric == 'roc_auc' else
                1.0 - float(average_precision_score(y, predictions)))
    if metric == 'rmse':
        return float(np.sqrt(mean_squared_error(y, predictions)))
    return float(mean_absolute_error(y, predictions))


def tune_family(x, y, numeric, categorical, family, task, metric, group,
                folds, trials, seed):
    """Optuna inner-fold search; all preprocessing refit within each training fold."""
    import numpy as np
    import optuna
    from ml.case_engine_v10 import fit_pipeline, propose, _pred
    x = x.reset_index(drop=True)
    y = y.reset_index(drop=True)
    splits = list(fold_indices(y, folds, seed, task, group))
    fold_cache: dict[int, list[float]] = {}
    def objective(trial):
        params = propose(trial, family, task)
        losses = []
        for tr, va in splits:
            model = fit_pipeline(numeric, categorical, family, task, params, x.iloc[tr], y.iloc[tr])
            pred = _pred(model, x.iloc[va], task)
            losses.append(primary_loss(y.iloc[va], pred, task, metric))
        fold_cache[trial.number] = losses
        return float(np.mean(losses))
    sampler = optuna.samplers.TPESampler(seed=seed)
    study = optuna.create_study(direction='minimize', sampler=sampler)
    study.optimize(objective, n_trials=trials, show_progress_bar=False, catch=())
    best = study.best_trial
    losses = fold_cache[best.number]
    return {'family': family, 'params': dict(best.params),
            'loss': float(best.value), 'fold_losses': [round(v, 7) for v in losses],
            'fold_sd': float(np.std(losses, ddof=1)) if len(losses) > 1 else 0.0,
            'trials': trials}


def staged_selection(x, y, numeric, categorical, config, task, group=None, seed=2026):
    """Two-stage family selection with a predeclared budget and choice rule."""
    metric = config['primary_metric']
    screen = [tune_family(x, y, numeric, categorical, name, task, metric, group,
                          config['inner_folds'], config['screen_trials'], seed + i)
              for i, name in enumerate(config['candidates'])]
    ranked = sorted(screen, key=lambda r: r['loss'])
    promoted = [r['family'] for r in ranked[:config['top_k']]]
    refined = [tune_family(x, y, numeric, categorical, name, task, metric, group,
                           config['inner_folds'], config['refine_trials'], seed + 100 + i)
               for i, name in enumerate(promoted)]
    decision = select_from_scores(refined, metric,
                    float(config.get('practical_tie_margin', DEFAULT_MARGIN[metric])))
    winner = next(r for r in refined if r['family'] == decision['family'])
    return {'screen': screen, 'promoted': promoted, 'refined': refined,
            'selection': decision, 'winner': winner}


def search(project: Path, config: dict, manifest: dict):
    """Explicit workstation-only nested selection, then refit DEVELOPMENT ONLY."""
    import numpy as np
    import pandas as pd
    import joblib
    from ml.case_engine_v10 import (load_data, split_data, fit_pipeline,
                                    selected_threshold, _pred)
    frame, y, dataset_sha = load_data(project, manifest)
    tr, va, te = split_data(frame, y, manifest)
    dev = np.sort(np.concatenate([tr, va]))
    contract = partition_contract(frame, y, dev, te, config, manifest)
    output_guard = (project/'artifacts'/'cases'/manifest['case_id']/'strategy_v13'/'selection.json')
    require(not output_guard.exists(), 'Existing selection: use a new case ID instead of overwriting evidence')
    num = manifest['features']['numeric']; cat = manifest['features']['categorical']
    x = frame.iloc[dev][num + cat].reset_index(drop=True)
    yy = y.iloc[dev].reset_index(drop=True)
    groups = (frame.iloc[dev][config['group_column']].to_numpy()
              if config.get('group_column') else None)
    outer_folds = list(fold_indices(yy, config['outer_folds'], 2126,
                                    manifest['task'], groups))
    outer_results = []
    for ix, (train, valid) in enumerate(outer_folds):
        subgroups = groups[train] if groups is not None else None
        selected = staged_selection(x.iloc[train], yy.iloc[train], num, cat,
                      config, manifest['task'], subgroups, seed=2026 + ix * 200)
        champion = selected['winner']
        model = fit_pipeline(num, cat, champion['family'], manifest['task'],
                             champion['params'], x.iloc[train], yy.iloc[train])
        predictions = _pred(model, x.iloc[valid], manifest['task'])
        loss = primary_loss(yy.iloc[valid], predictions, manifest['task'], config['primary_metric'])
        outer_results.append({'fold': ix + 1, 'train_n': int(len(train)),
           'assessment_n': int(len(valid)), 'selected_family': champion['family'],
           'outer_loss': round(float(loss), 7), 'promoted': selected['promoted']})
        print(f"OUTER FOLD {ix+1}/{len(outer_folds)}: winner={champion['family']} loss={loss:.5f}", flush=True)
    final = staged_selection(x, yy, num, cat, config, manifest['task'], groups, seed=5000)
    best = final['winner']
    winner = fit_pipeline(num, cat, best['family'], manifest['task'], best['params'], x, yy)
    # Fixed chosen hyperparameters: dev-only out-of-fold scores for threshold estimation.
    threshold = None
    if manifest['task'] == 'classification':
        oof = np.full(len(yy), np.nan)
        for t, v in fold_indices(yy, config['inner_folds'], 13013, manifest['task'], groups):
            mod = fit_pipeline(num, cat, best['family'], manifest['task'],
                               best['params'], x.iloc[t], yy.iloc[t])
            oof[v] = _pred(mod, x.iloc[v], manifest['task'])
        require(np.isfinite(oof).all(), 'OOF threshold scores incomplete')
        threshold = float(selected_threshold(yy, oof))
    from ml.case_engine_v10 import fit_pipeline as fit
    dummy = fit(num, cat, 'dummy', manifest['task'], {}, x, yy)
    output = (project / 'artifacts' / 'cases' / manifest['case_id'] / 'strategy_v13').resolve()
    require(output.is_relative_to((project/'artifacts').resolve()), 'Unsafe artifact path')
    output.mkdir(parents=True, exist_ok=True)
    require(not (output/'evaluation_once.json').exists(), 'Previously evaluated strategy; use new case ID')
    # Stable importable ml.case_engine_v10 adapters; never __main__ aliases.
    joblib.dump(winner, output/'winner_development_only.joblib')
    joblib.dump(dummy, output/'dummy_development_only.joblib')
    report = {
        'schema': SCHEMA, 'report_type': 'LOCAL_DEVELOPMENT_SELECTION_ONLY',
        'case_id': manifest['case_id'], 'dataset_sha256': dataset_sha,
        'manifest_sha256': manifest_hash(manifest), 'protocol_sha256': manifest_hash(config),
        'task': manifest['task'], 'primary_metric': config['primary_metric'],
        'metric_orientation': 'Loss, lower is better; AUC/AP converted to 1 - score',
        'holdout_status': config['holdout_status'], 'holdout_used_in_selection': False,
        'partition': contract, 'development_profile': development_profile(frame,y,dev,manifest),
        'outer_nested_results': outer_results,
        'outer_nested_mean_loss': round(float(np.mean([r['outer_loss'] for r in outer_results])), 7),
        'outer_nested_sd_loss': round(float(np.std([r['outer_loss'] for r in outer_results], ddof=1)), 7),
        'final_development_selection': final, 'selected_model': best['family'],
        'selected_params': best['params'], 'development_oof_threshold': threshold,
        'interpretation': 'Nested outer CV estimates the entire tuning/selection procedure; '
           'the final model is refitted on development only. Not site-external validation.',
        'privacy': 'Only aggregate metrics/metadata saved here; model binaries remain local.',
        'limitations': ['Later NHANES cycle previously inspected, not a fresh external test.',
                        'No NHANES complex-survey design inference or time-to-event endpoint.',
                        'Nested CV uncertainty reflects internal resampling only.']
    }
    (output/'selection.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print('LOCAL DEVELOPMENT SELECTION:', output/'selection.json')
    print('MODEL SAVED LOCALLY:', output/'winner_development_only.joblib')
    print('No evaluation cohort predictions or scores computed during model selection.')
    return report


def evaluate_once(project: Path, config: dict, manifest: dict):
    """Explicit sealed one-time assessment; *no fitting or model selection*."""
    import numpy as np
    import json
    from ml.case_engine_v10 import load_data, split_data, calculate_metrics, _pred
    from ml.case_model_io_v11 import load_canonical_trusted_model
    frame, y, digest = load_data(project, manifest)
    tr, va, te = split_data(frame, y, manifest)
    output = (project/'artifacts'/'cases'/manifest['case_id']/'strategy_v13').resolve()
    report_path = output/'selection.json'
    require(report_path.is_file(), 'Run --search on the workstation first')
    saved = json.loads(report_path.read_text())
    require(saved['schema'] == SCHEMA and saved['dataset_sha256'] == digest and
            saved['manifest_sha256'] == manifest_hash(manifest) and
            saved['protocol_sha256'] == manifest_hash(config),
            'Dataset/protocol/manifest changed: evaluation forbidden')
    seal = output/'evaluation_once.json'
    require(not seal.exists(), 'Holdout already evaluated under this strategy; repetition is blocked')
    cols = manifest['features']['numeric'] + manifest['features']['categorical']
    x_eval = frame.iloc[te][cols]
    y_eval = y.iloc[te]
    model = load_canonical_trusted_model(output/'winner_development_only.joblib')
    dummy = load_canonical_trusted_model(output/'dummy_development_only.joblib')
    pred = _pred(model, x_eval, manifest['task'])
    baseline = _pred(dummy, x_eval, manifest['task'])
    threshold = saved['development_oof_threshold'] if manifest['task'] == 'classification' else 0.5
    metrics = calculate_metrics(manifest['task'], y_eval, pred, pred, threshold)
    baseline_metrics = calculate_metrics(manifest['task'], y_eval, baseline, baseline)
    comparison = {'schema': SCHEMA, 'report_type': 'LOCAL_EXPLICIT_ONE_TIME_ASSESSMENT',
                  'case_id': manifest['case_id'], 'dataset_sha256': digest,
                  'holdout_status': config['holdout_status'],
                  'warning': ('Reused, previously inspected NHANES benchmark; not fresh independent validation'
                              if config['holdout_status'] == 'previously_inspected'
                              else 'One-time prespecified holdout evaluation'),
                  'selected_model': saved['selected_model'], 'metrics': metrics,
                  'dummy_baseline': baseline_metrics,
                  'model_selection_used_holdout': False,
                  'not_clinically_validated': True}
    # EXCLUSIVE create: failure if another process already sealed evaluation.
    with seal.open('x') as fp:
        fp.write(json.dumps(comparison, indent=2, allow_nan=False) + '\n')
    print('SEALED LOCAL EVALUATION:', seal)
    print('AGGREGATE METRICS:', json.dumps(metrics))
    print('No participant-level predictions saved or published.')
    return comparison


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project', default='.')
    ap.add_argument('--manifest', default='research/cases/nhanes_mortality_v10.json')
    ap.add_argument('--protocol', default='research/cases/nhanes_strategy_v13.json')
    modes = ap.add_mutually_exclusive_group(required=True)
    modes.add_argument('--plan', action='store_true', help='Dataset and split contract only; no fitting')
    modes.add_argument('--search', action='store_true', help='Staged nested CV training on workstation')
    modes.add_argument('--evaluate-once', action='store_true', help='Explicitly unseal holdout once; no fitting')
    ap.add_argument('--acknowledge-holdout', action='store_true')
    args = ap.parse_args()
    project = Path(args.project).resolve()
    spec = json.loads(within_project(project, args.manifest, 'research').read_text())
    protocol = json.loads(within_project(project, args.protocol, 'research').read_text())
    validate_protocol(protocol, spec)
    if args.plan:
        from ml.case_engine_v10 import load_data, split_data
        import numpy as np
        frame, y, sha = load_data(project, spec)
        tr, va, te = split_data(frame, y, spec)
        dev = np.sort(np.concatenate([tr, va]))
        contract = partition_contract(frame, y, dev, te, protocol, spec)
        print('PLAN VALID:', json.dumps({'case_id': spec['case_id'], 'dataset_sha256': sha,
              'partitions': contract, 'development_profile': development_profile(frame,y,dev,spec),
              'candidate_models': protocol['candidates'],
              'primary_metric': protocol['primary_metric'],
              'holdout_status': protocol['holdout_status'],
              'holdout_evaluated': False}, indent=2))
        print('No training, no model inference, no results published.')
    elif args.search:
        search(project, protocol, spec)
    else:
        require(args.acknowledge_holdout, 'Explicit --acknowledge-holdout required; '
                'existing NHANES benchmark already inspected')
        evaluate_once(project, protocol, spec)

if __name__ == '__main__':
    main()
