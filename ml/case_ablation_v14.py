"""FrailtyScope v0.14 — workstation-only exploratory feature/missingness ablations.

No import-time fitting or inference. Never evaluates the later-cycle holdout.
Keeps the v0.13-selected family and hyperparameters FIXED, using repeated identical
paired development folds. No model promotion, replacement or public export.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

SCHEMA = 'FRAILTYSCOPE_DEVELOPMENT_ABLATION_V14'


def ensure(ok: bool, why: str):
    if not ok:
        raise ValueError(why)


def sha_json(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode()).hexdigest()


def validate_config(config: dict, manifest: dict, strategy: dict, selection: dict) -> dict:
    """Pure validation: no dataset load or model-fitting side effects."""
    ensure(isinstance(config, dict) and config.get('schema') == SCHEMA, 'Invalid ablation schema')
    ensure(config.get('case_id') == manifest['case_id'] == strategy['case_id'], 'Case ID mismatch')
    ensure(selection.get('schema') == 'FRAILTYSCOPE_CASE_STRATEGY_V13',
           'Expected v0.13 development selection')
    ensure(selection.get('holdout_used_in_selection') is False, 'Selection touched holdout')
    ensure(selection.get('manifest_sha256') == sha_json(manifest), 'Manifest changed since selection')
    ensure(selection.get('protocol_sha256') == sha_json(strategy), 'Strategy changed since selection')
    ensure(selection.get('primary_metric') == strategy['primary_metric'], 'Selection metric mismatch')
    ensure(selection.get('selected_model') in strategy['candidates'], 'Invalid saved winner')
    ensure(isinstance(selection.get('selected_params'), dict), 'Missing winner hyperparameters')
    ensure(manifest['task'] in ('classification', 'regression'), 'Unsupported task')
    folds = config.get('folds')
    seeds = config.get('seeds')
    ensure(type(folds) is int and 2 <= folds <= 5, 'Use 2–5 development folds')
    ensure(isinstance(seeds, list) and 2 <= len(seeds) <= 6 and
           all(type(s) is int and 0 <= s <= 2**32-1 for s in seeds) and len(set(seeds)) == len(seeds),
           'Use 2–6 distinct integer seeds')
    variants = config.get('variants')
    ensure(isinstance(variants, list) and 2 <= len(variants) <= 8, 'Require 2–8 declared variants')
    ensure(all(isinstance(v, dict) for v in variants), 'Variant must be an object')
    names = [v.get('name') for v in variants]
    ensure(len(set(names)) == len(names) and names[0] == 'reference',
           'Unique variants required, with reference first')
    all_features = manifest['features']['numeric'] + manifest['features']['categorical']
    for v in variants:
        name = v.get('name')
        dropped = v.get('drop_features')
        flag = v.get('numeric_missing_indicators')
        ensure(isinstance(name, str) and name.isidentifier() and len(name) <= 55,
               'Invalid variant name')
        ensure(isinstance(dropped, list) and all(isinstance(z, str) for z in dropped)
               and len(dropped) == len(set(dropped)) and set(dropped).issubset(all_features),
               'Unexpected dropped predictor in '+name)
        ensure(type(flag) is bool, 'Missingness indicator flag must be boolean')
        ensure(len(dropped) < len(all_features), 'Variant cannot remove all predictors')
        ensure(not (name == 'reference' and (dropped or flag)),
               'Reference must use unchanged standard preprocessing')
    ensure(len({(tuple(sorted(v['drop_features'])), v['numeric_missing_indicators']) for v in variants})
           == len(variants), 'Duplicate experimental variants')
    return config


def columns_for(manifest: dict, variant: dict) -> tuple[list[str], list[str]]:
    removed = set(variant['drop_features'])
    return ([z for z in manifest['features']['numeric'] if z not in removed],
            [z for z in manifest['features']['categorical'] if z not in removed])


def model_pipeline(manifest: dict, selection: dict, variant: dict):
    """Construct unfitted fold-specific pipeline; fitting occurs only in --run."""
    from sklearn.pipeline import Pipeline
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from ml.case_engine_v10 import model_for
    numeric, categorical = columns_for(manifest, variant)
    transformers = []
    if numeric:
        transformers.append(('numeric', Pipeline([
            ('impute', SimpleImputer(strategy='median', keep_empty_features=True,
                                    add_indicator=variant['numeric_missing_indicators'])),
            ('scale', StandardScaler())]), numeric))
    if categorical:
        transformers.append(('category', Pipeline([
            ('impute', SimpleImputer(strategy='most_frequent')),
            ('encode', OneHotEncoder(handle_unknown='ignore', sparse_output=False))]), categorical))
    return Pipeline([
        ('features', ColumnTransformer(transformers, remainder='drop', sparse_threshold=0)),
        ('model', model_for(selection['selected_model'], manifest['task'], selection['selected_params']))
    ])


def summarize(repeat_scores: dict[str, list[dict]], metric: str, reference='reference') -> list[dict]:
    """Pure summarization of paired per-repeat scores, without model fitting."""
    import numpy as np
    ensure(reference in repeat_scores, 'Missing reference scores')
    baseline = repeat_scores[reference]
    ensure(baseline and all(isinstance(r.get('loss'), (float, int)) and math.isfinite(r['loss'])
                            for r in baseline), 'Invalid baseline')
    keys = [(r['seed'], r['n']) for r in baseline]
    result = []
    for name, rows in repeat_scores.items():
        ensure([(r['seed'], r['n']) for r in rows] == keys, 'Unpaired repeated CV summaries')
        losses = np.asarray([r['loss'] for r in rows], float)
        ensure(np.isfinite(losses).all(), 'Nonfinite metric')
        deltas = np.asarray([b['loss'] - r['loss'] for b, r in zip(baseline, rows)])
        result.append({'variant': name, 'metric': metric,
                       'repeated_cv_mean_loss': round(float(np.mean(losses)), 6),
                       'repeat_sd': round(float(np.std(losses, ddof=1)), 6) if len(losses)>1 else 0.,
                       'loss_gain_vs_reference': round(float(np.mean(deltas)), 6),
                       'per_repeat_loss_gain': [round(float(d), 6) for d in deltas],
                       'repeats_with_lower_loss': int((deltas > 0).sum()),
                       'repeats': len(rows)})
    return result


def load_context(project: Path, config_path: Path):
    from ml.case_strategy_v13 import validate_protocol, partition_contract
    from ml.case_engine_v10 import validate_manifest, load_data, split_data
    import numpy as np
    project = project.resolve()
    cfg = config_path.resolve()
    ensure(cfg.is_relative_to((project/'research').resolve()), 'Config must stay under research/')
    config = json.loads(cfg.read_text())
    # Do not guess case file paths: configuration pins the manifest and protocol.
    for key in ('manifest', 'strategy_protocol'):
        ensure(isinstance(config.get(key), str), 'Missing '+key+' path')
    def read_research(path: str):
        file = (project/path).resolve()
        ensure(file.is_relative_to((project/'research').resolve()) and file.is_file(),
               'Referenced file must exist under research/')
        return json.loads(file.read_text())
    manifest = validate_manifest(read_research(config['manifest']))
    strategy = validate_protocol(read_research(config['strategy_protocol']), manifest)
    spath = (project/'artifacts'/'cases'/manifest['case_id']/'strategy_v13'/'selection.json')
    ensure(spath.is_file(), 'Missing v0.13 development-only selection report')
    selection = json.loads(spath.read_text())
    validate_config(config, manifest, strategy, selection)
    frame, y, digest = load_data(project, manifest)
    ensure(selection.get('dataset_sha256') == digest, 'Dataset has changed since model selection')
    train, valid, eval_indices = split_data(frame, y, manifest)
    development = np.sort(np.concatenate([train, valid]))
    partition_contract(frame, y, development, eval_indices, strategy, manifest)
    # Restrict all subsequent operations to development only.
    cols = manifest['features']['numeric'] + manifest['features']['categorical']
    x = frame.iloc[development][cols].reset_index(drop=True)
    labels = y.iloc[development].reset_index(drop=True)
    groups = (frame.iloc[development][strategy['group_column']].to_numpy()
              if strategy.get('group_column') else None)
    return config, manifest, strategy, selection, digest, x, labels, groups


def run(project: Path, context: tuple) -> dict:
    """Fitting limited to the development partition, on the researcher's workstation."""
    import numpy as np
    from ml.case_engine_v10 import _pred
    from ml.case_strategy_v13 import fold_indices, primary_loss
    config, manifest, strategy, selection, digest, x, y, groups = context
    names = [v['name'] for v in config['variants']]
    repeated = {name: [] for name in names}
    metric = strategy['primary_metric']
    for seed in config['seeds']:
        partitions = list(fold_indices(y, config['folds'], seed, manifest['task'], groups))
        predictions = {name: np.full(len(y), np.nan) for name in names}
        for ix, (tr, va) in enumerate(partitions):
            for variant in config['variants']:
                num, cat = columns_for(manifest, variant)
                model = model_pipeline(manifest, selection, variant)
                model.fit(x.iloc[tr][num+cat], y.iloc[tr])
                predicted = np.asarray(_pred(model, x.iloc[va][num+cat], manifest['task']), float)
                ensure(len(predicted) == len(va) and np.isfinite(predicted).all(),
                       'Nonfinite fold predictions')
                predictions[variant['name']][va] = predicted
            print(f"DEV SEED {seed} FOLD {ix+1}/{len(partitions)} completed", flush=True)
        for variant in config['variants']:
            name = variant['name']
            p = predictions[name]
            ensure(np.isfinite(p).all(), 'Incomplete development OOF predictions')
            loss = primary_loss(y, p, manifest['task'], metric)
            repeated[name].append({'seed': seed, 'n': len(y), 'loss': round(float(loss), 8)})
        print('DEVELOPMENT REPEAT:', seed,
              {k: round(rows[-1]['loss'], 6) for k, rows in repeated.items()}, flush=True)
    summary = summarize(repeated, metric)
    return {
        'schema': SCHEMA, 'report_type':'LOCAL_EXPLORATORY_DEVELOPMENT_ABLATION_ONLY',
        'case_id':manifest['case_id'], 'dataset_sha256': digest,
        'manifest_sha256':sha_json(manifest), 'strategy_sha256':sha_json(strategy),
        'ablation_config_sha256':sha_json(config),
        'selected_model_fixed':selection['selected_model'],
        'selected_hyperparameters_fixed':selection['selected_params'],
        'n_development':len(y), 'n_evaluation_predictions_generated':0,
        'primary_metric':metric, 'metric_orientation':'Loss, lower is better',
        'variants':config['variants'], 'repeated_cv':repeated, 'comparison':summary,
        'selection_or_model_replacement_performed':False,
        'limitations':[
            'Exploratory post-selection diagnostic: hyperparameters selected earlier on the same development cohort.',
            'Repeated folds are not independent external assessments and gains are not inferential confidence intervals.',
            'No comparisons use the previously inspected evaluation cohort.',
            'No new clinical threshold or externally validated model selected.',
            'Missingness can be informative or reflect survey skip patterns; indicators do not establish causality.'
        ]}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan',action='store_true',help='Inspect development protocol only; no fitting')
    mode.add_argument('--run',action='store_true',help='Explicit workstation-only exploratory CV fitting')
    p.add_argument('--project',default='.')
    p.add_argument('--config',default='research/cases/nhanes_ablation_v14.json')
    a=p.parse_args();project=Path(a.project).resolve()
    context=load_context(project,project/a.config)
    config,manifest,strategy,selection,digest,x,y,groups=context
    if a.plan:
        missing=(x.isna().mean()*100).sort_values(ascending=False)
        print(json.dumps({'case_id':manifest['case_id'],'dataset_sha256':digest,
          'development_n':len(y),'selected_family_fixed':selection['selected_model'],
          'selected_params_fixed':selection['selected_params'],
          'evaluation_cohort_used':False, 'variants':[v['name'] for v in config['variants']],
          'high_missingness':[{ 'feature':str(k),'percent':round(float(v),2)}
                              for k,v in missing.items() if v>=10],
          'folds':config['folds'],'repeats':len(config['seeds']),
          'model_fitting':False},indent=2))
        print('PLAN ONLY. No model fitted, scores computed, or public files changed.')
        return
    out=(project/'artifacts'/'cases'/manifest['case_id']/'ablation_v14'/sha_json(config)[:12]).resolve()
    ensure(out.is_relative_to((project/'artifacts'/'cases').resolve()), 'Unsafe output path')
    output=out/'development_ablation.json'
    ensure(not output.exists(), 'Existing ablation result: refuse overwrite')
    report=run(project,context)
    out.mkdir(parents=True,exist_ok=True)
    with output.open('x') as f:
        f.write(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('LOCAL ABLATION REPORT:',output)
    print('DEVELOPMENT COMPARISONS:',json.dumps(report['comparison'],indent=2))
    print('No model selected/replaced. No evaluation predictions or public exports.')

if __name__=='__main__':main()
