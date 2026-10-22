"""FrailtyScope v0.16 — development-only joint model/preprocessing selection.

No fitting or prediction at import time. `--plan` performs *no model fitting*.
`--run` fits ONLY on the workstation's development cohort. Existing v0.13/v0.15
artifacts and the later-cycle evaluation are not changed, read for scores, or used
for selection. Output contains aggregate model-search metadata and a LOCAL binary.

Experimental limitation: NHANES development data have informed earlier candidate
choices. Repeated/nested CV is exploratory reuse, not external validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

SCHEMA = 'FRAILTYSCOPE_JOINT_SELECTION_V16'
SUPPORTED = {
    'classification': {'logistic', 'random_forest', 'hist_boost', 'xgboost', 'catboost'},
    'regression': {'ridge', 'random_forest', 'hist_boost', 'xgboost', 'catboost'},
}
COMPLEXITY = {'logistic':0, 'ridge':0, 'hist_boost':1, 'random_forest':2,
              'catboost':3, 'xgboost':4}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode('utf-8')).hexdigest()


def pair_name(family, variant):
    return f'{family}__{variant}'


def candidate_pairs(config):
    return [(family, policy['name']) for family in config['families']
            for policy in config['variants']]


def estimated_fit_count(config, reference_grid_size):
    pairs = len(candidate_pairs(config))
    inner = config['inner_folds']
    per_outer = (pairs * config['screen_trials']
                 + config['top_k'] * config['refine_trials']
                 + reference_grid_size) * inner + 2
    final = (pairs * config['screen_trials']
             + config['top_k'] * config['refine_trials']) * inner
    final += inner + 1  # final winner OOF threshold + development fit
    return len(config['outer_seeds']) * config['outer_folds'] * per_outer + final


def validate_config(config, manifest, strategy):
    """Pure reusable case contract; no previous experiment is required."""
    from ml.case_strategy_v13 import METRICS, validate_protocol
    require(isinstance(config, dict) and config.get('schema') == SCHEMA, 'Invalid v0.16 schema')
    require(config.get('case_id') == manifest.get('case_id') == strategy.get('case_id'),
            'Case ID mismatch')
    validate_protocol(strategy, manifest)
    require(config.get('metric') == strategy['primary_metric']
            and config['metric'] in METRICS[manifest['task']], 'Inconsistent task/metric')
    require(config.get('holdout_policy') == 'development_only_no_evaluation',
            'Evaluation is not permitted by v0.16')
    require(type(config.get('prior_exploration_of_development')) is bool,
            'Explicitly acknowledge whether prior analyses explored this development cohort')
    families = config.get('families')
    require(isinstance(families, list) and 2 <= len(families) <= 5
            and len(families) == len(set(families))
            and all(f in SUPPORTED[manifest['task']] and f in strategy['candidates']
                    and f in manifest['models'] for f in families), 'Invalid families')
    variants = config.get('variants')
    require(isinstance(variants,list) and 2 <= len(variants) <= 8 and
            all(isinstance(v,dict) for v in variants), 'Require declared preprocessing policies')
    names = [v.get('name') for v in variants]
    require(len(set(names))==len(names) and names[0]=='reference' and
            'missingness_indicators' in names and
            all(isinstance(name,str) and name.isidentifier() and len(name)<=50 for name in names),
            'Require reference and missingness-indicator policies with unique names')
    features = manifest['features']['numeric']+manifest['features']['categorical']
    for variant in variants:
        drops = variant.get('drop_features')
        indicator = variant.get('numeric_missing_indicators')
        require(isinstance(drops,list) and len(drops)==len(set(drops)) and
                all(isinstance(f,str) and f in features for f in drops) and
                len(drops)<len(features) and type(indicator) is bool,
                'Invalid predictor-removal or missingness policy')
        if variant['name']=='reference':
            require(not drops and not indicator, 'Reference must be original preprocessing')
        if variant['name']=='missingness_indicators':
            require(not drops and indicator, 'Missingness policy must preserve all predictors')
    require(len({(tuple(sorted(v['drop_features'])),v['numeric_missing_indicators'])
                 for v in variants})==len(variants), 'Duplicate preprocessing definitions')
    for key, low, high in [('outer_folds',2,5), ('inner_folds',2,5),
                            ('screen_trials',1,8), ('refine_trials',2,25), ('top_k',1,5)]:
        require(type(config.get(key)) is int and low <= config[key] <= high,
                'Invalid '+key)
    require(config['refine_trials'] >= config['screen_trials']
            and config['top_k'] < len(candidate_pairs(config)), 'Invalid stage budgets')
    seeds = config.get('outer_seeds')
    require(isinstance(seeds,list) and 1 <= len(seeds) <= 3
            and len(set(seeds)) == len(seeds)
            and all(type(v) is int and 1 <= v <= 2**31-1 for v in seeds),
            'Invalid distinct outer seeds')
    margin = config.get('practical_tie_margin')
    require(type(margin) in (int,float) and math.isfinite(margin)
            and 0 <= margin <= .02, 'Invalid practical margin')
    require(config.get('baseline_family') == ('logistic' if manifest['task']=='classification'
            else 'ridge') and config['baseline_family'] in families,
            'Require regularized logistic/ridge reference model')
    require(config['baseline_family'] + '__reference' in
            {pair_name(*p) for p in candidate_pairs(config)}, 'Reference pair unavailable')
    grid = config.get('baseline_regularization_grid')
    require(isinstance(grid,list) and 3 <= len(grid) <= 15 and
            len(set(grid))==len(grid) and all(type(v) in (float,int)
            and math.isfinite(v) and 0.001 <= v <= 100 for v in grid) and
            all(grid[i]<grid[i+1] for i in range(len(grid)-1)),
            'Invalid baseline regularization grid')
    require(estimated_fit_count(config, len(grid)) <= 2000,
            'Projected fitting budget exceeds 2000; reduce folds/trials/families')
    return config


def select_pair(records, margin):
    """Predeclared practical-loss tie: simpler family then reference preprocessing.

    This is not a statistical equivalence claim or a holdout-based selection.
    """
    require(isinstance(records,list) and records, 'No candidate records')
    pairs = [pair_name(r['family'],r['variant']) for r in records]
    require(len(set(pairs))==len(pairs), 'Repeated candidate combination')
    for r in records:
        require(r.get('family') in COMPLEXITY and isinstance(r.get('variant'),str) and r['variant'].isidentifier() and
                type(r.get('loss')) in (int,float) and math.isfinite(r['loss'])
                and isinstance(r.get('params'),dict), 'Invalid candidate evidence')
    require(type(margin) in (int,float) and math.isfinite(margin) and margin>=0,
            'Invalid tie margin')
    minimum = min(r['loss'] for r in records)
    eligible = [r for r in records if r['loss'] <= minimum + margin + 1e-12]
    chosen = min(eligible, key=lambda r:(COMPLEXITY[r['family']],
                0 if r['variant']=='reference' else 1, r['loss'],r['family']))
    return {'family':chosen['family'],'variant':chosen['variant'],
            'pair':pair_name(chosen['family'],chosen['variant']),
            'parameters':chosen['params'],'inner_cv_loss':round(chosen['loss'],7),
            'best_available_loss':round(minimum,7),
            'practical_tie_margin':margin,
            'within_tie_margin':[pair_name(r['family'],r['variant']) for r in eligible],
            'rule':'Minimum inner-CV loss; within declared practical margin prefer simpler model and original preprocessing'}


def paired_summary(records):
    """Pure paired repeated CV summary. Repeats are correlated, not replicates."""
    import numpy as np
    require(records and all(type(r.get('reference_loss')) in (int,float)
             and type(r.get('joint_loss')) in (int,float)
             and math.isfinite(r['reference_loss']) and math.isfinite(r['joint_loss'])
             for r in records), 'Invalid repeat losses')
    ids = [r['seed'] for r in records]
    require(len(ids)==len(set(ids)), 'Duplicate repeat seed')
    diffs = [r['reference_loss']-r['joint_loss'] for r in records]
    return {'reference_mean_brier_or_loss':round(float(np.mean([r['reference_loss'] for r in records])),7),
            'joint_mean_brier_or_loss':round(float(np.mean([r['joint_loss'] for r in records])),7),
            'mean_gain_vs_reference':round(float(np.mean(diffs)),7),
            'gains_by_repeat':[round(d,7) for d in diffs],
            'repeats_improved':int(sum(d>0 for d in diffs)),
            'repeats':len(records),
            'interpretation':'Exploratory paired development nested CV on reused participants; not external validation'}


def locate_context(project:Path,config_path:Path):
    """Read a case manifest and strategy directly; no v0.13–v0.15 RUN prerequisite."""
    import numpy as np
    from ml.case_engine_v10 import validate_manifest, load_data, split_data
    from ml.case_strategy_v13 import validate_protocol, partition_contract
    project=project.resolve(); cfg=config_path.resolve()
    research=(project/'research').resolve()
    require(cfg.is_relative_to(research) and cfg.is_file(),
            'v0.16 protocol must exist in research/')
    config=json.loads(cfg.read_text())
    def read_research(key):
        rel=config.get(key)
        require(isinstance(rel,str) and rel, 'Missing research file reference: '+key)
        path=(project/rel).resolve()
        require(path.is_relative_to(research) and path.is_file(),
                'Research file must exist under research/: '+key)
        return json.loads(path.read_text())
    manifest=validate_manifest(read_research('manifest'))
    strategy=validate_protocol(read_research('strategy_protocol'),manifest)
    validate_config(config,manifest,strategy)
    frame,y,data_sha=load_data(project,manifest)
    train,valid,holdout=split_data(frame,y,manifest)
    dev=np.sort(np.concatenate([train,valid]))
    partition_contract(frame,y,dev,holdout,strategy,manifest)
    columns=manifest['features']['numeric']+manifest['features']['categorical']
    x=frame.iloc[dev][columns].reset_index(drop=True)
    labels=y.iloc[dev].reset_index(drop=True)
    groups=(frame.iloc[dev][strategy['group_column']].to_numpy()
            if strategy.get('group_column') else None)
    return config,manifest,strategy,{'variants':config['variants']},data_sha,x,labels,groups


def _build(manifest,ablation,family,variant,params):
    from ml.case_ablation_v14 import model_pipeline,columns_for
    match=next(z for z in ablation['variants'] if z['name']==variant)
    num,cat=columns_for(manifest,match)
    return model_pipeline(manifest, {'selected_model':family,'selected_params':params},match),num+cat


def _fit_predict(x,y,tr,va,manifest,ablation,family,variant,params):
    import numpy as np
    from ml.case_engine_v10 import _pred
    fitted,cols=_build(manifest,ablation,family,variant,params)
    fitted.fit(x.iloc[tr][cols],y.iloc[tr])
    pred=np.asarray(_pred(fitted,x.iloc[va][cols],manifest['task']),float)
    require(len(pred)==len(va) and np.isfinite(pred).all(),
            'Incomplete or invalid predicted values')
    if manifest['task']=='classification':
        require(((pred>=0)&(pred<=1)).all(),'Probabilities outside unit interval')
    return pred


def _tune_pair(x,y,groups,manifest,ablation,config,family,variant,trials,seed):
    """Model fitting only after explicit workstation --run."""
    import numpy as np
    import optuna
    from ml.case_engine_v10 import propose
    from ml.case_strategy_v13 import fold_indices,primary_loss
    folds=list(fold_indices(y,config['inner_folds'],seed,manifest['task'],groups))
    def objective(trial):
        params=propose(trial,family,manifest['task'])
        losses=[]
        for tr,va in folds:
            pred=_fit_predict(x,y,tr,va,manifest,ablation,family,variant,params)
            losses.append(primary_loss(y.iloc[va],pred,manifest['task'],config['metric']))
        return float(np.mean(losses))
    sampler=optuna.samplers.TPESampler(seed=seed)
    study=optuna.create_study(direction='minimize',sampler=sampler)
    study.optimize(objective,n_trials=trials,show_progress_bar=False)
    require(math.isfinite(study.best_value),'Nonfinite tuning objective')
    return {'family':family,'variant':variant,'loss':float(study.best_value),
            'params':dict(study.best_params),'trials':trials}


def _joint_select(x,y,groups,manifest,ablation,config,seed):
    screening=[_tune_pair(x,y,groups,manifest,ablation,config,family,variant,
                          config['screen_trials'],seed+10*i)
               for i,(family,variant) in enumerate(candidate_pairs(config))]
    promoted=sorted(screening,key=lambda r:(r['loss'],COMPLEXITY[r['family']],r['variant']))[:config['top_k']]
    refinement=[_tune_pair(x,y,groups,manifest,ablation,config,r['family'],r['variant'],
                           config['refine_trials'],seed+1000+11*i)
                for i,r in enumerate(promoted)]
    selection=select_pair(refinement,float(config['practical_tie_margin']))
    return {'screening':screening,
            'promoted_pairs':[pair_name(r['family'],r['variant']) for r in promoted],
            'refined':refinement,'selection':selection}


def _reference_search(x,y,groups,manifest,ablation,config,grid,seed):
    """Independently tune baseline on same inner folds (no convenient straw man)."""
    import numpy as np
    from ml.case_strategy_v13 import fold_indices,primary_loss
    splits=list(fold_indices(y,config['inner_folds'],seed,manifest['task'],groups))
    family=config['baseline_family']
    param='C' if family=='logistic' else 'alpha'
    losses=[]
    for v in grid:
        results=[]
        for tr,va in splits:
            pred=_fit_predict(x,y,tr,va,manifest,ablation,family,'reference',{param:float(v)})
            results.append(primary_loss(y.iloc[va],pred,manifest['task'],config['metric']))
        losses.append((float(np.mean(results)),float(v)))
    best=min(losses,key=lambda t:(t[0],t[1]))
    return {param:best[1]},best[0]


def run(context):
    """All fitting happens here, on explicit --run; development rows ONLY."""
    import numpy as np
    import optuna
    from ml.case_strategy_v13 import fold_indices,primary_loss
    config,manifest,strategy,ablation,data_sha,x,y,groups=context
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    records=[];fold_records=[]
    for seed in config['outer_seeds']:
        n=len(y); reference=np.full(n,np.nan); joint=np.full(n,np.nan)
        folds=list(fold_indices(y,config['outer_folds'],seed,manifest['task'],groups))
        for fold,(train,valid) in enumerate(folds,1):
            train_x=x.iloc[train].reset_index(drop=True)
            train_y=y.iloc[train].reset_index(drop=True)
            train_groups=groups[train] if groups is not None else None
            decision=_joint_select(train_x,train_y,train_groups,manifest,ablation,config,seed+fold*1200)
            champion=decision['selection']
            baseline_params,baseline_inner=_reference_search(
                train_x,train_y,train_groups,manifest,ablation,config,
                config['baseline_regularization_grid'],seed+fold*1210)
            pred_joint=_fit_predict(x,y,train,valid,manifest,ablation,
                                    champion['family'],champion['variant'],champion['parameters'])
            pred_ref=_fit_predict(x,y,train,valid,manifest,ablation,
                                  config['baseline_family'],'reference',baseline_params)
            joint[valid]=pred_joint; reference[valid]=pred_ref
            fold_records.append({'seed':seed,'fold':fold,'assessment_n':len(valid),
                'selected_pair':champion['pair'],'selected_inner_loss':champion['inner_cv_loss'],
                'baseline_inner_loss':round(baseline_inner,7),
                'promoted_pairs':decision['promoted_pairs']})
            print(f'JOINT DEVELOPMENT seed={seed} fold={fold}/{len(folds)} '
                  f"selected={champion['pair']}",flush=True)
        require(np.isfinite(joint).all() and np.isfinite(reference).all(),'OOF incomplete')
        reference_loss=primary_loss(y,reference,manifest['task'],config['metric'])
        joint_loss=primary_loss(y,joint,manifest['task'],config['metric'])
        records.append({'seed':seed,'n':len(y),'reference_loss':round(float(reference_loss),8),
                        'joint_loss':round(float(joint_loss),8)})
        print(f'JOINT NESTED REPEAT {seed}: reference={reference_loss:.6f}, '
              f'joint={joint_loss:.6f}',flush=True)
    full=_joint_select(x,y,groups,manifest,ablation,config,seed=17116)
    chosen=full['selection']
    final_model,cols=_build(manifest,ablation,chosen['family'],chosen['variant'],
                            chosen['parameters'])
    final_model.fit(x[cols],y)
    # Derived only from development, never using previously inspected holdout.
    threshold=None
    if manifest['task']=='classification':
        from ml.case_engine_v10 import selected_threshold
        scores=np.full(len(y),np.nan)
        for train,valid in fold_indices(y,config['inner_folds'],22116,manifest['task'],groups):
            scores[valid]=_fit_predict(x,y,train,valid,manifest,ablation,
                chosen['family'],chosen['variant'],chosen['parameters'])
        require(np.isfinite(scores).all(),'Development threshold OOF incomplete')
        threshold=float(selected_threshold(y,scores))
    stats=paired_summary(records)
    freq=Counter(row['selected_pair'] for row in fold_records)
    report={'schema':SCHEMA,'report_type':'LOCAL_EXPLORATORY_JOINT_DEVELOPMENT_ONLY',
            'case_id':manifest['case_id'],'dataset_sha256':data_sha,
            'manifest_sha256':digest_json(manifest),
            'strategy_sha256':digest_json(strategy),
            'v16_protocol_sha256':digest_json(config),
            'preprocessing_definitions':config['variants'],
            'prior_exploration_of_development':config['prior_exploration_of_development'],
            'task':manifest['task'],'primary_metric':config['metric'],
            'cohort':{'development_n':int(len(y)), 'evaluation_predictions_generated':0},
            'models_and_policies':list(map(lambda p:pair_name(*p),candidate_pairs(config))),
            'fold_details':fold_records,'fold_selection_counts':dict(freq),
            'repeated_nested':records,'comparison':stats,
            'final_development_selection':full,
            'selected_model':chosen['family'],'selected_preprocessing':chosen['variant'],
            'selected_parameters':chosen['parameters'],
            'development_oof_threshold':threshold,
            'model_saved_locally_only':True,'holdout_scored':False,
            'clinical_deployment_permitted':False,'public_export':False,
            'limitations':[
                'Candidate policies motivated by earlier analyses of the same development participants.',
                'Outer-fold nested estimates assess the joint selection procedure, not the fitted final model.',
                'Repeated resampling on the same people is not independent validation.',
                'No later NHANES survey cycle was used for model/preprocessing selection or scoring.',
                'No survey-design-aware uncertainty intervals or clinical threshold justification.',
                'The selected model is a research artifact, not a deployed prediction service.'
            ]}
    return report,final_model



def validate_local_release(config: dict, report: dict, model_exists: bool) -> dict:
    """Pure source-only publication gate: never deserialize or evaluate a model.

    Verify the actual nested-report schema. Preprocessing options in the manifest
    are OBJECTS with `name` fields; the selected report value is a STRING.
    No dataset, private artifact content beyond aggregate report, or model loaded.
    """
    require(isinstance(config, dict) and isinstance(report, dict),
            'Invalid release manifest/report')
    require(report.get('schema') == SCHEMA and
            report.get('report_type') == 'LOCAL_EXPLORATORY_JOINT_DEVELOPMENT_ONLY',
            'Not a local development-only joint-selection report')
    require(report.get('case_id') == config.get('case_id') and
            report.get('v16_protocol_sha256') == digest_json(config),
            'Case or protocol fingerprint does not match the saved report')
    require(model_exists is True, 'Expected locally saved development model is missing')
    require(report.get('cohort', {}).get('evaluation_predictions_generated') == 0 and
            report.get('holdout_scored') is False, 'Evaluation cohort was used')
    require(report.get('model_saved_locally_only') is True and
            report.get('clinical_deployment_permitted') is False and
            report.get('public_export') is False,
            'Unapproved model/publication status')
    require(report.get('preprocessing_definitions') == config.get('variants'),
            'Saved preprocessing definitions differ from release configuration')
    allowed_variants = {v['name'] for v in config['variants']}
    allowed_pairs = {pair_name(*pair) for pair in candidate_pairs(config)}
    selected_model = report.get('selected_model')
    selected_variant = report.get('selected_preprocessing')
    require(selected_model in config['families'] and selected_variant in allowed_variants,
            'Unknown selected model family or preprocessing policy')
    selected_pair = pair_name(selected_model, selected_variant)
    require(selected_pair in allowed_pairs, 'Selected model/preprocessing pair invalid')
    require(report.get('final_development_selection', {}).get('selection', {}).get('pair') == selected_pair,
            'Final selected recipe and summary disagree')
    require(set(report.get('models_and_policies', [])) == allowed_pairs,
            'Screened candidates differ from declared candidate pairs')
    fold_details = report.get('fold_details', [])
    repeats = report.get('repeated_nested', [])
    require(len(fold_details) == config['outer_folds'] * len(config['outer_seeds']) and
            len(repeats) == len(config['outer_seeds']),
            'Nested fold/repeat count mismatch')
    require(all(row.get('selected_pair') in allowed_pairs for row in fold_details),
            'Nested fold used an undeclared candidate')
    require(all(row.get('seed') in config['outer_seeds'] and
                math.isfinite(row.get('reference_loss', float('nan'))) and
                math.isfinite(row.get('joint_loss', float('nan'))) for row in repeats),
            'Invalid or nonfinite paired-development scores')
    return {'case_id': report['case_id'], 'selected_pair': selected_pair,
            'outer_assessments': len(fold_details), 'repeats': len(repeats),
            'holdout_scored': False, 'model_kept_local': True}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    mode=ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan',action='store_true',help='No fitting or holdout inference')
    mode.add_argument('--run',action='store_true',help='Explicit workstation-only nested training')
    ap.add_argument('--project',default='.')
    ap.add_argument('--config',default='research/cases/nhanes_joint_selection_v16.json')
    args=ap.parse_args();project=Path(args.project).resolve()
    context=locate_context(project,project/args.config)
    config,manifest,strategy,ablation,data_sha,x,y,groups=context
    out=(project/'artifacts'/'cases'/manifest['case_id']/
         'joint_selection_v16'/digest_json(config)[:12]).resolve()
    require(out.is_relative_to((project/'artifacts'/'cases').resolve()),
            'Unsafe output path')
    report_file=out/'joint_selection.json';model_file=out/'winner_development_only.joblib'
    if args.plan:
        print('V16 JOINT PLAN:',json.dumps({'case_id':manifest['case_id'],
            'dataset_sha256':data_sha,'task':manifest['task'],
            'development_n':len(y),'holdout_evaluated':False,
            'candidate_pairs':[pair_name(*p) for p in candidate_pairs(config)],
            'outer_folds':config['outer_folds'],'inner_folds':config['inner_folds'],
            'outer_repeats':len(config['outer_seeds']),
            'screen_trials':config['screen_trials'],'refine_trials':config['refine_trials'],
            'top_k':config['top_k'],
            'upper_estimated_fits':estimated_fit_count(config,len(config['baseline_regularization_grid'])),
            'training':False,'model_overwrite':False},indent=2))
        print('PLAN ONLY. No model fitting, holdout prediction, or public export.')
        return
    require(not report_file.exists() and not model_file.exists(),
            'Existing v0.16 evidence: refusal to overwrite')
    report,model=run(context)
    out.mkdir(parents=True,exist_ok=True)
    import joblib
    # Retain both files locally in ignored artifacts/, do not stage for GitHub.
    joblib.dump(model,model_file)
    with report_file.open('x') as fp:
        json.dump(report,fp,indent=2,allow_nan=False)
        fp.write('\n')
    print('LOCAL JOINT SELECTION:',report_file)
    print('LOCAL DEVELOPMENT MODEL:',model_file)
    print('SELECTED RECIPE:',json.dumps({'model':report['selected_model'],
          'preprocessing':report['selected_preprocessing'],
          'parameters':report['selected_parameters'],
          'development_oof_threshold':report['development_oof_threshold'],
          'nested_comparison':report['comparison']},indent=2))
    print('No evaluation predictions, patient-level exports, or public model promotion.')


if __name__=='__main__':main()
