"""FrailtyScope v0.17: workstation-only nested selection stability and calibration.

Runs ONLY when explicitly invoked with --run. Never scores the previously inspected
NHANES evaluation cohort, replaces earlier models, or exports any participant rows.
All probabilities are ephemeral. Repeated outer folds reuse the same individuals:
these are diagnostic internal CV results, NOT independent clinical validation.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

SCHEMA = 'FRAILTYSCOPE_LOCAL_SELECTION_STABILITY_V17'
CONFIG_SCHEMA = 'FRAILTYSCOPE_STABILITY_PROTOCOL_V17'


def require(condition, explanation):
    if not condition:
        raise ValueError(explanation)


def verify_config(config: dict, joint: dict, manifest: dict) -> dict:
    """No data read, model fitting or model deserialization."""
    from ml.case_joint_selection_v16 import validate_config, estimated_fit_count, digest_json
    require(isinstance(config, dict) and config.get('schema') == CONFIG_SCHEMA,
            'Unsupported v0.17 stability protocol')
    require(config.get('case_id') == joint.get('case_id') == manifest.get('case_id'),
            'Case identifiers disagree')
    require(isinstance(config.get('v16_config'), str) and bool(config['v16_config']),
            'Missing v0.16 config path')
    require(config.get('v16_protocol_sha256') == digest_json(joint),
            'v0.16 protocol fingerprint changed')
    require(config.get('metric') == joint.get('metric'), 'Metric changed since joint selection')
    require(config.get('holdout_policy') == 'development_only_no_evaluation',
            'Any evaluation-cohort access for scoring is forbidden')
    require(config.get('prior_development_exploration') is True,
            'Reused development participants must be explicitly acknowledged')
    seeds = config.get('outer_seeds')
    require(isinstance(seeds, list) and 2 <= len(seeds) <= 4 and
            all(type(v) is int and 1 <= v <= 2**31-1 for v in seeds) and
            len(set(seeds)) == len(seeds), 'Expected 2–4 distinct reproducible outer seeds')
    require(not set(seeds).intersection(joint.get('outer_seeds', [])),
            'Use new fold seeds to diagnose sensitivity; not new individuals')
    repeats = config.get('permutation_repeats')
    require(type(repeats) is int and 1 <= repeats <= 5, 'Invalid permutation repeat budget')
    require(type(config.get('calibration_bins')) is int and
            3 <= config['calibration_bins'] <= 10, 'Invalid calibration bin count')
    require(type(config.get('min_calibration_bin_n')) is int and
            30 <= config['min_calibration_bin_n'] <= 200, 'Invalid minimum calibration bin count')
    require(type(config.get('importance_top_k')) is int and
            3 <= config['importance_top_k'] <= 20, 'Invalid importance top-k')
    require(type(config.get('max_estimated_fits')) is int and
            50 <= config['max_estimated_fits'] <= 2400, 'Invalid workstation fitting limit')
    # v0.16 cost includes an additional final-development fit, so this bound is conservative.
    projected = estimated_fit_count({**joint, 'outer_seeds': seeds},
                                    len(joint['baseline_regularization_grid']))
    require(projected <= config['max_estimated_fits'],
            f'Projected {projected} fold fits exceed configured workstation budget')
    require(config['importance_top_k'] <= len(manifest['features']['numeric'] +
                                               manifest['features']['categorical']),
            'Top-k exceeds number of predictors')
    return {'estimated_fit_upper_bound': projected,
            'repeated_outer_assessments': len(seeds) * joint['outer_folds'],
            'candidate_pairs': len(joint['families']) * len(joint['variants'])}


def equal_frequency_calibration(y, probability, bins: int, min_bin_n: int):
    """OOF calibration table, not fitted calibration or a threshold decision."""
    import numpy as np
    yy = np.asarray(y, dtype=int)
    pp = np.asarray(probability, dtype=float)
    require(len(yy) == len(pp) and len(yy) >= bins*min_bin_n and
            set(yy).issubset({0, 1}) and len(set(yy)) == 2 and
            np.isfinite(pp).all() and ((pp>=0)&(pp<=1)).all(),
            'Cannot calculate binary OOF calibration')
    order = np.argsort(pp, kind='stable')
    groups = np.array_split(order, bins)
    table=[]
    for i, idx in enumerate(groups, 1):
        require(len(idx) >= min_bin_n, 'Calibration bin is too small')
        table.append({'bin': i, 'n': int(len(idx)),
                      'mean_prediction': round(float(pp[idx].mean()), 6),
                      'observed_rate': round(float(yy[idx].mean()), 6)})
    ece = sum(row['n']/len(yy)*abs(row['observed_rate']-row['mean_prediction'])
              for row in table)
    return {'bins':table, 'ece_descriptive':round(float(ece),6),
            'mean_prediction':round(float(pp.mean()),6),
            'observed_prevalence':round(float(yy.mean()),6),
            'mean_probability_minus_prevalence':round(float(pp.mean()-yy.mean()),6)}


def paired_diagnostics(y, joint, reference, task):
    import numpy as np
    yy=np.asarray(y); a=np.asarray(joint,float); b=np.asarray(reference,float)
    require(len(yy)==len(a)==len(b) and len(yy)>=20 and
            np.isfinite(a).all() and np.isfinite(b).all(), 'Unpaired or invalid OOF predictions')
    if task=='classification':
        from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
        require(len(set(yy))==2 and set(yy).issubset({0,1}) and
                ((a>=0)&(a<=1)).all() and ((b>=0)&(b<=1)).all(),
                'Invalid binary OOF probabilities')
        return {'n':len(yy),
                'joint':{'brier':round(float(brier_score_loss(yy,a)),7),
                         'roc_auc':round(float(roc_auc_score(yy,a)),6),
                         'average_precision':round(float(average_precision_score(yy,a)),6)},
                'reference':{'brier':round(float(brier_score_loss(yy,b)),7),
                             'roc_auc':round(float(roc_auc_score(yy,b)),6),
                             'average_precision':round(float(average_precision_score(yy,b)),6)},
                'brier_gain_vs_reference':round(float(brier_score_loss(yy,b)-brier_score_loss(yy,a)),7)}
    require(task=='regression','Unknown task')
    return {'n':len(yy), 'joint':{'rmse':round(float(np.sqrt(np.mean((yy-a)**2))),7),
                                  'mae':round(float(np.mean(np.abs(yy-a))),7)},
            'reference':{'rmse':round(float(np.sqrt(np.mean((yy-b)**2))),7),
                         'mae':round(float(np.mean(np.abs(yy-b))),7)}}


def summarize_selection(folds: list[dict], allowed: list[str]) -> dict:
    require(folds and isinstance(allowed,list) and len(allowed)==len(set(allowed)),
            'Invalid selection ledger')
    counts=Counter()
    for row in folds:
        pair=row.get('selected_pair')
        require(pair in allowed,'Undeclared fold winner')
        counts[pair]+=1
    n=len(folds)
    # These are frequencies of *repeated folds*, not independent sample proportions.
    return {'assessments':n,
            'pair_frequency':[{'pair':name,'selected_folds':counts[name],
                               'fraction':round(counts[name]/n,4)} for name in allowed],
            'preprocessing_frequency':dict(sorted(Counter(row['selected_pair'].split('__',1)[1]
                                                        for row in folds).items())),
            'model_frequency':dict(sorted(Counter(row['selected_pair'].split('__',1)[0]
                                               for row in folds).items())),
            'distinct_pairs_selected':sum(v>0 for v in counts.values())}


def summarize_importance(records: list[dict], predictors: list[str], top_k: int):
    """Fold-held-out permutation diagnostics; omitted variables remain 'not assessed'."""
    import numpy as np
    require(records and len(predictors)==len(set(predictors)), 'No valid importance ledger')
    by_feature=defaultdict(list)
    top_counts=Counter()
    for record in records:
        scores=record.get('feature_drops')
        require(isinstance(scores,dict) and bool(scores) and
                set(scores).issubset(predictors) and
                all(type(v) in (int,float) and math.isfinite(v) for v in scores.values()),
                'Invalid fold-level importance vector')
        for key,value in scores.items():by_feature[key].append(float(value))
        top=sorted(scores,key=lambda x:(-scores[x],x))[:min(top_k,len(scores))]
        top_counts.update(top)
    n=len(records)
    rows=[]
    for name in predictors:
        data=by_feature.get(name,[])
        rows.append({'feature':name,'assessed_folds':len(data),
             'mean_metric_decrease':round(float(np.mean(data)),7) if data else None,
             'fold_sd':round(float(np.std(data,ddof=1)),7) if len(data)>1 else None,
             'top_k_fraction_all_folds':round(top_counts[name]/n,4)})
    return sorted(rows,key=lambda row:(row['mean_metric_decrease'] is None,
                         -(row['mean_metric_decrease'] or 0), row['feature']))


def load_context(project:Path,config_path:Path):
    from ml.case_joint_selection_v16 import locate_context,digest_json,validate_local_release
    project=project.resolve();config_path=config_path.resolve()
    require(config_path.is_relative_to((project/'research').resolve()) and config_path.is_file(),
            'Stability config must be a file inside research/')
    config=json.loads(config_path.read_text())
    rel=config.get('v16_config')
    require(isinstance(rel,str) and bool(rel),'Missing v0.16 protocol path')
    previous=(project/rel).resolve()
    require(previous.is_relative_to((project/'research').resolve()) and previous.is_file(),
            'v0.16 protocol must exist under research/')
    original_context=locate_context(project,previous)
    joint,manifest,strategy,ablation,sha,x,y,groups=original_context
    metadata=verify_config(config,joint,manifest)
    # Version-locked older selection is provenance, not an outcome used in new selection.
    prior_path=(project/'artifacts'/'cases'/manifest['case_id']/'joint_selection_v16'/
                digest_json(joint)[:12]/'joint_selection.json')
    require(prior_path.is_file(), 'Missing completed local v0.16 selection ledger')
    prior=json.loads(prior_path.read_text())
    model_path=prior_path.parent/'winner_development_only.joblib'
    validate_local_release(joint,prior,model_path.is_file()) # no model loading
    require(prior.get('dataset_sha256')==sha and
            prior.get('manifest_sha256')==digest_json(manifest) and
            prior.get('strategy_sha256')==digest_json(strategy),
            'Existing selection does not match current dataset and design')
    return config,original_context,metadata


def run(context):
    """EXPLICIT workstation-only repeated nested fits; development observations only."""
    import numpy as np
    import optuna
    from sklearn.inspection import permutation_importance
    from ml.case_joint_selection_v16 import (_joint_select,_reference_search,_build,
                                              pair_name,candidate_pairs)
    from ml.case_strategy_v13 import fold_indices
    from ml.case_engine_v10 import _pred
    config,existing,metadata=context
    joint,manifest,strategy,ablation,sha,x,y,groups=existing
    require(manifest['task'] in ('classification','regression'), 'Unsupported task')
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    predictors=manifest['features']['numeric']+manifest['features']['categorical']
    permitted=[pair_name(*pair) for pair in candidate_pairs(joint)]
    fold_records=[];repeat_records=[];importance_records=[]
    for seed in config['outer_seeds']:
        n=len(y);joint_oof=np.full(n,np.nan);ref_oof=np.full(n,np.nan)
        splits=list(fold_indices(y,joint['outer_folds'],seed,manifest['task'],groups))
        for fold,(tr,va) in enumerate(splits,1):
            xtrain=x.iloc[tr].reset_index(drop=True)
            ytrain=y.iloc[tr].reset_index(drop=True)
            train_groups=groups[tr] if groups is not None else None
            select=_joint_select(xtrain,ytrain,train_groups,manifest,ablation,joint,
                                 seed+fold*1200)
            chosen=select['selection']
            baseline_params,_=_reference_search(xtrain,ytrain,train_groups,manifest,ablation,
                                joint,joint['baseline_regularization_grid'],seed+fold*1210)
            # Fit ONCE on outer-train for each assessed model; do not refit on assessment.
            model,cols=_build(manifest,ablation,chosen['family'],chosen['variant'],chosen['parameters'])
            model.fit(x.iloc[tr][cols],y.iloc[tr])
            baseline,bcols=_build(manifest,ablation,joint['baseline_family'],'reference',baseline_params)
            baseline.fit(x.iloc[tr][bcols],y.iloc[tr])
            joint_preds=np.asarray(_pred(model,x.iloc[va][cols],manifest['task']),float)
            reference_preds=np.asarray(_pred(baseline,x.iloc[va][bcols],manifest['task']),float)
            require(len(joint_preds)==len(va)==len(reference_preds) and
                    np.isfinite(joint_preds).all() and np.isfinite(reference_preds).all(),
                    'Invalid outer-fold predictions')
            if manifest['task']=='classification':
                require(((joint_preds>=0)&(joint_preds<=1)).all() and
                        ((reference_preds>=0)&(reference_preds<=1)).all(),
                        'Outer-fold score outside probability range')
            joint_oof[va]=joint_preds;ref_oof[va]=reference_preds
            # Permutation on independent *development* fold, never the evaluated cohort.
            scoring = 'neg_brier_score' if manifest['task']=='classification' else 'neg_mean_squared_error'
            importance=permutation_importance(model,x.iloc[va][cols],y.iloc[va],
                            scoring=scoring,n_repeats=config['permutation_repeats'],
                            random_state=seed+fold,n_jobs=1)
            deltas={name:round(float(val),8) for name,val in zip(cols,importance.importances_mean)}
            require(set(deltas).issubset(predictors), 'Importance dimensions incompatible')
            importance_records.append({'seed':seed,'fold':fold,'feature_drops':deltas})
            fold_records.append({'seed':seed,'fold':fold,'n_assessment':len(va),
                'selected_pair':chosen['pair'],'selected_inner_loss':chosen['inner_cv_loss'],
                'promoted_pairs':select['promoted_pairs']})
            print(f'STABILITY DEV seed={seed} fold={fold}/{len(splits)} pair={chosen["pair"]}',flush=True)
        require(np.isfinite(joint_oof).all() and np.isfinite(ref_oof).all(),
                'Incomplete development OOF scores')
        metrics=paired_diagnostics(y,joint_oof,ref_oof,manifest['task'])
        record={'seed':seed,'paired_metrics':metrics}
        if manifest['task']=='classification':
            record['joint_calibration']=equal_frequency_calibration(
                y,joint_oof,config['calibration_bins'],config['min_calibration_bin_n'])
            record['reference_calibration']=equal_frequency_calibration(
                y,ref_oof,config['calibration_bins'],config['min_calibration_bin_n'])
        repeat_records.append(record)
        msg=('brier_gain='+str(metrics['brier_gain_vs_reference']) if manifest['task']=='classification'
             else 'rmse='+str(metrics['joint']['rmse']))
        print(f'STABILITY DEVELOPMENT REPEAT {seed}: {msg}',flush=True)
    frequencies=summarize_selection(fold_records,permitted)
    importance=summarize_importance(importance_records,predictors,config['importance_top_k'])
    from ml.case_joint_selection_v16 import digest_json
    return {'schema':SCHEMA, 'report_type':'LOCAL_DEVELOPMENT_STABILITY_DIAGNOSTICS_ONLY',
        'case_id':manifest['case_id'],'dataset_sha256':sha,
        'manifest_sha256':digest_json(manifest),
        'v16_protocol_sha256':digest_json(joint),
        'stability_protocol_sha256':digest_json(config),
        'cohort':{'development_n':len(y),'evaluation_predictions_generated':0},
        'selection_stability':frequencies,
        'fold_selections':fold_records,
        'repeated_development_metrics':repeat_records,
        'importance_stability':importance,
        'holdout_scored':False,'existing_model_replaced':False,'public_export':False,
        'n_model_binaries_exported':0,
        'limitations':['Repeated outer folds overlap in people, so frequency is not external selection probability.',
           'Development data previously informed candidate model and missingness-policy choices.',
           'Calibration and permutation importance are measured only on development out-of-fold predictions.',
           'Permuting correlated predictors can obscure their collective contribution.',
           'Feature rankings are descriptive, not causal and not clinically validated.',
           'No evaluation-cohort results, models or participant rows are exported.']}


def validate_local_report(config, joint, manifest, result):
    """Release-time pure validation only; no model inference or data loading."""
    from ml.case_joint_selection_v16 import digest_json,pair_name,candidate_pairs
    require(isinstance(result,dict) and result.get('schema')==SCHEMA and
            result.get('report_type')=='LOCAL_DEVELOPMENT_STABILITY_DIAGNOSTICS_ONLY',
            'Invalid stability report schema')
    require(result.get('case_id')==manifest.get('case_id')==config.get('case_id') and
            result.get('v16_protocol_sha256')==digest_json(joint) and
            result.get('stability_protocol_sha256')==digest_json(config) and
            result.get('manifest_sha256')==digest_json(manifest),
            'Case or protocol fingerprint mismatch')
    require(result.get('holdout_scored') is False and
            result.get('cohort',{}).get('evaluation_predictions_generated')==0 and
            result.get('existing_model_replaced') is False and
            result.get('public_export') is False and
            result.get('n_model_binaries_exported')==0,
            'Evaluation/preview/model boundary violated')
    folds=result.get('fold_selections',[])
    permitted={pair_name(*c) for c in candidate_pairs(joint)}
    require(len(folds)==len(config['outer_seeds'])*joint['outer_folds'] and
            all(r.get('selected_pair') in permitted for r in folds),
            'Nested selection ledger inconsistent')
    require(len(result.get('repeated_development_metrics',[]))==len(config['outer_seeds']),
            'Missing repeated development metrics')
    require(len(result.get('importance_stability',[]))==
            len(manifest['features']['numeric']+manifest['features']['categorical']),
            'Incomplete feature stability report')
    return {'case_id':result['case_id'],'outer_assessments':len(folds),
            'holdout_scored':False,'models_exported':0}


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    mode=cli.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan',action='store_true',help='Dataset/protocol preflight, no model training')
    mode.add_argument('--run',action='store_true',help='Run nested selection stability on THIS workstation')
    cli.add_argument('--project',default='.')
    cli.add_argument('--config',default='research/cases/nhanes_stability_v17.json')
    args=cli.parse_args();project=Path(args.project).resolve()
    context=load_context(project,project/args.config)
    config,existing,meta=context
    joint,manifest,strategy,ablation,sha,x,y,groups=existing
    if args.plan:
        print('V17 DEVELOPMENT STABILITY PLAN:',json.dumps({'case_id':manifest['case_id'],
            'dataset_sha256':sha,'development_n':len(y),
            'outer_assessments':meta['repeated_outer_assessments'],
            'candidate_pairs':meta['candidate_pairs'],
            'conservative_fit_upper_bound':meta['estimated_fit_upper_bound'],
            'permutation_repeats':config['permutation_repeats'],
            'holdout_scored':False,'training':False},indent=2))
        print('No model training, holdout scoring or outputs changed.')
        return
    from ml.case_joint_selection_v16 import digest_json
    output=(project/'artifacts'/'cases'/manifest['case_id']/'stability_v17'/
            digest_json(config)[:12]/
            'selection_stability.json').resolve()
    require(output.is_relative_to((project/'artifacts'/'cases').resolve()),
            'Output must remain inside ignored artifacts/cases/')
    require(not output.exists(), 'Existing stability evidence: refusal to overwrite')
    result=run(context)
    validate_local_report(config,joint,manifest,result)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as fp:
        json.dump(result,fp,indent=2,allow_nan=False);fp.write('\n')
    print('LOCAL STABILITY REPORT:',output)
    print('SELECTION FREQUENCY:',json.dumps(result['selection_stability'],indent=2))
    print('No evaluation outcomes or participant-level scores saved or published.')


if __name__=='__main__': main()
