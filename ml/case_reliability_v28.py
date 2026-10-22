"""FrailtyScope v0.28 -- synthetic-only OOF reliability diagnostics.

The CLI reads source-controlled JSON and (in --audit) an existing PRIVATE
metadata-only v0.27 report. It cannot open participant data, fit models, load
model binaries or score held-out NHANES outcomes. In-memory routines are ONLY
for invented fixtures; synthetic_fixture=True is NOT a security mechanism.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np

from ml.case_foldsafe_v25 import local_file, validate_partition
from ml.case_task_models_v26 import CANDIDATES, METRICS, validate_design as validate_v26

SCHEMA = 'FRAILTYSCOPE_RELIABILITY_PROTOCOL_V28'
REPORT_SCHEMA = 'FRAILTYSCOPE_PRIVATE_RELIABILITY_REVIEW_V28'
EXEC_SCHEMA = 'FRAILTYSCOPE_SYNTHETIC_OOF_RELIABILITY_V28'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode()).hexdigest()


def validate_design(cfg, v27, v26, recipe):
    require(isinstance(cfg, dict) and cfg.get('schema') == SCHEMA,
            'Unknown reliability protocol')
    require(cfg.get('case_id') == v27.get('case_id') == v26.get('case_id') == recipe.get('case_id'),
            'Case identity changed')
    for key in ('holdout_history', 'prior_exploration', 'prediction_index_status'):
        require(cfg.get(key) == v27.get(key) == v26.get(key) == recipe.get(key),
                'Previously documented study history cannot be reset: '+key)
    require(cfg.get('related_v27_protocol') and cfg.get('related_private_v27_review'),
            'Previous source and private metadata lineage required')
    require(cfg.get('scope') == 'synthetic_only_blueprint' and all(cfg.get(key) is False for key in (
        'real_data_execution_permitted', 'model_fitting_permitted', 'holdout_scoring_permitted',
        'clinical_use_permitted', 'public_export_permitted')),
        'Source-only reliability protocol cannot authorize real research analysis')
    require(cfg.get('task') == v26.get('task') == v27.get('source_task'),
            'Do not replace the original study task')
    require(cfg['task'] in ('classification', 'regression'),
            'Survival/longitudinal reliability requires specialist metrics and validation')
    require(cfg.get('split_policy') == v26.get('split_policy') == recipe.get('split_review'),
            'Reliability split policy differs from predecessor')
    require(cfg.get('n_splits') == v26.get('n_splits'),
            'Reliability fold count differs from predecessor')
    require(cfg.get('source_predictions') == 'synthetic_out_of_fold_only' and
            cfg.get('selection_context') == 'development_exploratory' and
            cfg.get('independent_evaluation') is False,
            'OOF diagnostics are not independent evaluation or tuning authorization')
    require(cfg.get('threshold_policy') == 'no_threshold_selection' and
            cfg.get('recalibration_policy') == 'diagnose_only',
            'No evaluation-driven threshold tuning or recalibration in v0.28')
    require(cfg.get('uncertainty_unit') == 'participant' and
            cfg.get('bootstrap_type') == 'paired_fixed_prediction_cluster_percentile',
            'Resampling must be paired at participant level')
    require(type(cfg.get('seed')) is int and 0 <= cfg['seed'] < 2**32,
            'Invalid random seed')
    require(type(cfg.get('bootstrap_replicates')) is int and
            50 <= cfg['bootstrap_replicates'] <= 500,
            'Bounded bootstrap count required')
    require(type(cfg.get('calibration_bins')) is int and 3 <= cfg['calibration_bins'] <= 10,
            'Bounded diagnostic bin count required')
    require(type(cfg.get('minimum_bin_count')) is int and 3 <= cfg['minimum_bin_count'] <= 30,
            'Minimum bin support required')
    require(type(cfg.get('minimum_unique_people')) is int and
            10 <= cfg['minimum_unique_people'] <= 100,
            'Minimum independent group count required')
    candidates=cfg.get('candidate_names')
    allowed={c['name'] for c in v26.get('candidates', [])}
    require(isinstance(candidates,list) and len(candidates)>=2 and
            len(set(candidates))==len(candidates) and set(candidates)<=allowed,
            'Candidates must be prespecified, unique and in v0.26 registry')
    require(cfg.get('reference_candidate') in candidates and
            cfg['reference_candidate']==('dummy_prior' if cfg['task']=='classification' else 'dummy_mean'),
            'Require original v0.26 dummy baseline')
    require(cfg.get('primary_metric') == v26.get('primary_metric') and
            cfg['primary_metric'] in METRICS[cfg['task']],
            'Primary metric cannot be changed after development comparison')
    return cfg


def make_plan(cfg):
    return {'schema':REPORT_SCHEMA, 'case_id':cfg['case_id'],
            'config_sha256':digest(cfg), 'route':'BLOCKED_FOR_NEW_ANALYSIS',
            'task':cfg['task'], 'diagnostics':['oof_metrics','calibration_bins' if cfg['task']=='classification'
                       else 'regression_residuals','paired_group_bootstrap','probability_shift_stress'
                       if cfg['task']=='classification' else 'residual_shift_stress'],
            'candidate_names':cfg['candidate_names'],
            'minimum_unique_people':cfg['minimum_unique_people'],
            'bootstrap_replicates':cfg['bootstrap_replicates'],
            'index_status':cfg['prediction_index_status'],
            'holdout_history':cfg['holdout_history'],
            'no_participant_tables_opened':True,'no_models_fitted':True,
            'no_predictions_generated':True,'no_holdout_targets_accessed':True,
            'public_export':False, 'synthetic_only':True,
            'limitations':[
                'Fixed OOF development predictions are not a fresh independent test set.',
                'Cluster resampling of fixed predictions ignores model fitting, selection, and tuning variability.',
                'Calibration bins and slope are descriptive; no fitted calibrator is applied.',
                'Perturbation checks change predictions artificially, not the clinical data distribution.',
                'Survey design, time-to-event censoring, longitudinal dropout and transport uncertainty not covered.',
                'The previously inspected NHANES later cycle cannot become pristine validation.'
            ]}


def _execution_guard(cfg):
    require(isinstance(cfg,dict) and cfg.get('schema')==SCHEMA and
            cfg.get('scope')=='synthetic_only_blueprint' and
            cfg.get('source_predictions')=='synthetic_out_of_fold_only' and
            cfg.get('selection_context')=='development_exploratory' and
            cfg.get('independent_evaluation') is False and
            cfg.get('threshold_policy')=='no_threshold_selection' and
            cfg.get('recalibration_policy')=='diagnose_only' and
            cfg.get('uncertainty_unit')=='participant' and
            cfg.get('bootstrap_type')=='paired_fixed_prediction_cluster_percentile' and
            cfg.get('task') in ('classification','regression') and
            type(cfg.get('n_splits')) is int and 2<=cfg['n_splits']<=5 and
            type(cfg.get('bootstrap_replicates')) is int and 50<=cfg['bootstrap_replicates']<=500 and
            type(cfg.get('seed')) is int and 0<=cfg['seed']<2**32 and
            type(cfg.get('minimum_bin_count')) is int and 3<=cfg['minimum_bin_count']<=30 and
            type(cfg.get('calibration_bins')) is int and 3<=cfg['calibration_bins']<=10 and
            type(cfg.get('minimum_unique_people')) is int and cfg['minimum_unique_people']>=10 and
            isinstance(cfg.get('candidate_names'),list) and len(cfg['candidate_names'])>=2 and
            len(set(cfg['candidate_names']))==len(cfg['candidate_names']) and
            cfg.get('reference_candidate') in cfg['candidate_names'] and
            cfg.get('reference_candidate') == ('dummy_prior' if cfg['task']=='classification' else 'dummy_mean') and
            cfg.get('primary_metric') in METRICS[cfg['task']] and
            cfg.get('split_policy') in ('person_disjoint','forward_time','person_and_forward_time') and
            all(cfg.get(k) is False for k in (
                'real_data_execution_permitted','model_fitting_permitted',
                'holdout_scoring_permitted','clinical_use_permitted','public_export_permitted')),
            'Synthetic-only reliability configuration invalid')


def _one_dim(vals, n, label):
    v=np.asarray(vals)
    require(v.ndim==1 and len(v)==n and v.dtype.kind in 'iuf' and
            np.isfinite(v).all(), 'Invalid numeric '+label)
    return v.astype(float)


def _checked_fold(cfg, entry):
    require(isinstance(entry,dict) and isinstance(entry.get('predictions'),dict),
            'Require fold with matching predictions')
    require(set(entry['predictions'])==set(cfg['candidate_names']),
            'Every candidate must provide predictions for identical held-out rows')
    tr=entry.get('train_ids'); va=entry.get('valid_ids')
    tg=entry.get('train_people'); vg=entry.get('valid_people')
    require(tr is not None and va is not None and tg is not None and vg is not None and
            len(tr)==len(tg) and len(va)==len(vg) and len(tr)>=3 and len(va)>=2,
            'Need row IDs and participant IDs for every fold')
    require(all(isinstance(z,(str,int,np.integer)) and str(z) for z in list(tr)+list(va)+list(tg)+list(vg)),
            'Invalid group/row identifiers')
    require(len(set(tr))==len(tr) and len(set(va))==len(va),
            'Duplicate row IDs within fold')
    require(len(set(tg))>=2 and len(set(vg))>=1,
            'Insufficient participant groups')
    # All diagnostic policies guard PEOPLE, even when timestamps are also checked.
    temporal=cfg['split_policy'] in ('forward_time','person_and_forward_time')
    tt=entry.get('train_time'); vt=entry.get('valid_time')
    validate_partition(tr,va,policy='person_and_forward_time' if temporal else 'person_disjoint',
                       train_groups=tg,valid_groups=vg,
                       train_time=tt,valid_time=vt)
    n=len(va)
    y=_one_dim(entry.get('truth'),n,'held-out truth')
    if cfg['task']=='classification':
        require(set(y.tolist())=={0.0,1.0},
                'Each held-out classification fold needs events and non-events')
    else:
        require(np.std(y)>0,'Regression validation outcomes must vary')
    pred={name:_one_dim(entry['predictions'][name],n,'predictions '+name)
          for name in cfg['candidate_names']}
    if cfg['task']=='classification':
        require(all(((v>=0)&(v<=1)).all() for v in pred.values()),
                'Probabilities outside [0,1]')
    return y,pred,va,vg


def _scores(task, truth, predicted):
    from sklearn.metrics import (brier_score_loss,log_loss,roc_auc_score,
                                 average_precision_score,mean_absolute_error,
                                 mean_squared_error,r2_score)
    if task=='classification':
        eps=1e-12
        return {'brier':float(brier_score_loss(truth,predicted)),
                'log_loss':float(log_loss(truth,np.clip(predicted,eps,1-eps),labels=[0,1])),
                'roc_auc':float(roc_auc_score(truth,predicted)),
                'average_precision':float(average_precision_score(truth,predicted))}
    return {'mae':float(mean_absolute_error(truth,predicted)),
            'rmse':float(np.sqrt(mean_squared_error(truth,predicted))),
            'r2':float(r2_score(truth,predicted))}


def _calibration(truth,pred, bins, min_count):
    """Diagnostic calibration only. This is NOT a fitted correction."""
    from scipy.optimize import minimize
    binned=[];edges=np.linspace(0,1,bins+1)
    ix=np.minimum(np.searchsorted(edges,pred,side='right')-1,bins-1)
    for k in range(bins):
        subset=ix==k
        if int(subset.sum())<min_count:
            continue  # Do not report misleading tiny-bin event fractions.
        binned.append({'interval':[float(edges[k]),float(edges[k+1])],
                       'n':int(subset.sum()), 'mean_prediction':float(np.mean(pred[subset])),
                       'observed_fraction':float(np.mean(truth[subset]))})
    # Descriptive logistic recalibration slope/intercept on OOF predictions.
    # Require positive/negative cases and sufficiently varied logits.
    eps=1e-6;z=np.log(np.clip(pred,eps,1-eps)/np.clip(1-pred,eps,1-eps))
    result={'bins':binned,'bins_suppressed':int(bins-len(binned)),
            'mean_predicted_risk':float(np.mean(pred)),
            'observed_event_rate':float(np.mean(truth)),
            'intercept':None,'slope':None,'slope_status':'not_estimable'}
    if len(truth)<30 or len(set(truth.tolist()))<2 or np.std(z)<1e-5:
        return result
    from scipy.special import expit
    X=np.column_stack([np.ones(len(z)),z])
    def objective(w):
        eta=X@w
        loss=np.logaddexp(0,eta).sum()-truth@eta
        grad=X.T@(expit(eta)-truth)
        return float(loss),grad
    try:
        fit=minimize(objective,np.array([0.,1.]),jac=True,method='L-BFGS-B',
                     options={'maxiter':250,'ftol':1e-10})
        if fit.success and np.isfinite(fit.x).all() and abs(fit.x[1])<=30 and abs(fit.x[0])<=30:
            result.update(intercept=float(fit.x[0]),slope=float(fit.x[1]),
                          slope_status='descriptive_in_sample_on_oof')
    except (ValueError,FloatingPointError,OverflowError):
        pass
    return result


def _paired_loss(task,y,p):
    if task=='classification':return (y-p)**2
    return np.abs(y-p)


def _boot(cfg, y, groups, pred):
    """Cluster percentile intervals for FIXED predictions, not model-fit uncertainty."""
    unit=list(dict.fromkeys(groups))
    require(len(unit)>=cfg['minimum_unique_people'],
            'Not enough independent participants for grouped uncertainty')
    location={x:np.flatnonzero(np.array(groups,dtype=object)==x) for x in unit}
    rng=np.random.default_rng(cfg['seed'])
    baseline=_paired_loss(cfg['task'],y,pred[cfg['reference_candidate']])
    result={}
    for name in cfg['candidate_names']:
        if name==cfg['reference_candidate']:continue
        loss=_paired_loss(cfg['task'],y,pred[name])-baseline
        observed=float(np.mean(loss))
        vals=[]
        for _ in range(cfg['bootstrap_replicates']):
            sampled=rng.integers(0,len(unit),len(unit))
            ix=np.concatenate([location[unit[j]] for j in sampled])
            vals.append(float(np.mean(loss[ix])))
        low,high=np.quantile(vals,[.025,.975])
        result[name]={'paired_mean_loss_difference':observed,
                      'conditional_95pct_cluster_percentile_interval':[float(low),float(high)],
                      'loss_definition':'brier_component' if cfg['task']=='classification'
                                        else 'absolute_error',
                      'negative_favors_candidate':True}
    return result


def assess_synthetic_oof(cfg, fold_records, *, synthetic_fixture=False):
    """Analyze synthetic precomputed OOF predictions; no model training or I/O.

    Each record has train_ids/valid_ids, train_people/valid_people,
    truth and predictions with the SAME validation-row order. An absent
    timestamp is invalid for a forward-time design. The caller must produce
    genuine fold-out predictions; the metadata checks cannot prove provenance.
    """
    require(synthetic_fixture is True,'Real research prediction analysis is not authorized')
    _execution_guard(cfg)
    require(isinstance(fold_records,list) and len(fold_records)==cfg['n_splits'],
            'Exactly the declared number of OOF folds required')
    yy=[];group=[];all_pred={name:[] for name in cfg['candidate_names']}
    valid_ids=[];valid_groups=[]
    for entry in fold_records:
        truth,pred,ids,people=_checked_fold(cfg,entry)
        yy.extend(truth.tolist());valid_ids.extend(ids);valid_groups.extend(people)
        group.extend(people)
        for name in all_pred:all_pred[name].extend(pred[name].tolist())
    require(len(valid_ids)==len(set(valid_ids)),
            'Validation row scored in more than one fold')
    require(len(valid_groups)==len(set(valid_groups)) or
            all(sum(x in set(e['valid_people']) for e in fold_records)==1
                for x in set(valid_groups)),
            'Participant assigned to validation in multiple folds')
    require(len(set(group))>=cfg['minimum_unique_people'],
            'Too few distinct validation participants')
    y=np.asarray(yy,dtype=float);pred={k:np.asarray(v,dtype=float) for k,v in all_pred.items()}
    require(len(y)>=30, 'Too few synthetic OOF observations')
    if cfg['task']=='classification':
        require(sum(y==0)>=8 and sum(y==1)>=8,
                'Too few positive or negative outcomes for calibration diagnostics')
    metrics={name:_scores(cfg['task'],y,p) for name,p in pred.items()}
    diagnostics={}
    for name,p in pred.items():
        if cfg['task']=='classification':
            diagnostics[name]=_calibration(y,p,cfg['calibration_bins'],cfg['minimum_bin_count'])
        else:
            residual=y-p
            diagnostics[name]={'mean_residual':float(np.mean(residual)),
                               'median_absolute_residual':float(np.median(np.abs(residual))),
                               'n_synthetic_residuals':int(len(residual))}
    perturbation={}
    for name,p in pred.items():
        changes={}
        for shift in (-0.05,0.05):
            altered=np.clip(p+shift,1e-6,1-1e-6) if cfg['task']=='classification' else p+shift
            key='minus_0_05' if shift<0 else 'plus_0_05'
            metric='brier' if cfg['task']=='classification' else 'mae'
            changes[key]=float(_scores(cfg['task'],y,altered)[metric]-metrics[name][metric])
        perturbation[name]=changes
    return {'schema':EXEC_SCHEMA,'task':cfg['task'], 'config_sha256':digest(cfg),
            'n_folds':len(fold_records),'n_synthetic_validation_rows':len(y),
            'n_independent_people':len(set(group)),
            'metrics_oof_pooled':metrics,'calibration_or_residual_diagnostics':diagnostics,
            'paired_fixed_prediction_group_bootstrap':_boot(cfg,y,group,pred),
            'artificial_score_shift_sensitivity':perturbation,
            'development_predictions_only':True,'independent_validation':False,
            'selection_adjusted_intervals':False,'model_refitting_in_bootstrap':False,
            'recalibration_performed':False, 'predictive_models_fitted':False,
            'descriptive_calibration_regression_estimated':any(
                row.get('slope_status')=='descriptive_in_sample_on_oof'
                for row in diagnostics.values()) if cfg['task']=='classification' else False,
            'private_data_accessed':False,'participant_predictions_exported':False,
            'clinical_use_permitted':False}


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    actions=cli.add_mutually_exclusive_group(required=True)
    actions.add_argument('--plan',action='store_true')
    actions.add_argument('--audit',action='store_true')
    cli.add_argument('--project',default='.')
    cli.add_argument('--config',default='research/cases/nhanes_reliability_v28.json')
    args=cli.parse_args()
    root=Path(args.project).resolve()
    cfg=json.loads(local_file(root,args.config,'research').read_text())
    v27=json.loads(local_file(root,cfg['related_v27_protocol'],'research').read_text())
    v26=json.loads(local_file(root,v27['related_v26_protocol'],'research').read_text())
    v25=json.loads(local_file(root,v26['related_v25_protocol'],'research').read_text())
    from ml.case_governance_v22 import validate_protocol as check22
    from ml.case_dictionary_timing_v23 import validate_protocol as check23
    from ml.case_harmonization_v24 import validate_protocol as check24
    from ml.case_foldsafe_v25 import validate_recipe
    from ml.case_temporal_v27 import validate_design as check27, digest as digest27
    v23=json.loads(local_file(root,v25['related_v23_protocol'],'research').read_text())
    v24=json.loads(local_file(root,v25['related_v24_protocol'],'research').read_text())
    v22=json.loads(local_file(root,v23['related_v22_protocol'],'research').read_text())
    manifest=json.loads(local_file(root,v23['case_manifest'],'research').read_text())
    check22(v22);check23(v23,manifest,v22);check24(v24,v23)
    validate_recipe(v25,v23,v24);validate_v26(v26,v25,manifest)
    check27(v27,v26,v25)
    validate_design(cfg,v27,v26,v25)
    report=make_plan(cfg)
    if args.audit:
        path=local_file(root,cfg['related_private_v27_review'],'artifacts')
        require(path.suffix=='.json' and path.stat().st_size<250_000,
                'Invalid private predecessor metadata path')
        parent=json.loads(path.read_text())
        require(parent.get('schema')=='FRAILTYSCOPE_PRIVATE_TEMPORAL_REVIEW_V27' and
                parent.get('config_sha256')==digest27(v27) and
                parent.get('case_id')==cfg['case_id'] and
                parent.get('v26_private_metadata_verified') is True and
                parent.get('route')=='BLOCKED_FOR_NEW_ANALYSIS' and
                parent.get('no_participant_tables_opened') is True and
                parent.get('no_models_fitted') is True and
                parent.get('no_predictions_generated') is True and
                parent.get('no_holdout_targets_accessed') is True and
                parent.get('public_export') is False,
                'Private v0.27 predecessor metadata is invalid')
        report['v27_private_metadata_verified']=True
    print('V28 RELIABILITY AND UNCERTAINTY PLAN:',json.dumps({k:report[k] for k in (
        'case_id','route','task','diagnostics','candidate_names','minimum_unique_people',
        'bootstrap_replicates','holdout_history','index_status')},indent=2))
    if args.audit:
        target=(root/'artifacts/cases'/cfg['case_id']/'reliability_v28'/
                digest(cfg)[:12]/'reliability_review.json').resolve()
        require(target.is_relative_to((root/'artifacts/cases').resolve()) and
                not target.exists(),'Immutable private v0.28 review already exists')
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x') as stream:
            json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
        print('PRIVATE IMMUTABLE METADATA REVIEW:',target)
    else:
        print('PLAN ONLY. Source metadata reviewed, no private audit/report opened.')
    print('No participant records, research labels, model fitting, predictions or held-out outcomes accessed.')


if __name__=='__main__':main()
