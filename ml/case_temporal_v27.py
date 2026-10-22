"""FrailtyScope v0.27: synthetic-only survival and next-visit forecasting foundations.

The CLI reads SOURCE contracts and optionally an existing PRIVATE metadata JSON;
it never opens participant data or fits a real model. Toy in-memory evaluators
are for invented fixtures ONLY. Their flag is not an access-control sandbox.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from ml.case_foldsafe_v25 import build_preprocessor, expected_columns, local_file

SCHEMA = 'FRAILTYSCOPE_TEMPORAL_PROTOCOL_V27'
REPORT_SCHEMA = 'FRAILTYSCOPE_PRIVATE_TEMPORAL_REVIEW_V27'
TASKS = ('right_censored_survival', 'next_observed_visit_regression')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode()).hexdigest()


def validate_design(cfg, v26, recipe):
    require(isinstance(cfg, dict) and cfg.get('schema') == SCHEMA, 'Unknown v0.27 contract')
    require(cfg.get('case_id') == v26.get('case_id') == recipe.get('case_id'), 'Case mismatch')
    for key in ('holdout_history', 'prior_exploration', 'prediction_index_status'):
        require(cfg.get(key) == v26.get(key) == recipe.get(key),
                'Cannot alter historical data/holdout/timing evidence: '+key)
    require(cfg.get('related_v26_protocol') and cfg.get('related_private_v26_review'),
            'Source and private documentary predecessor required')
    require(cfg.get('scope') == 'synthetic_only_blueprint' and
            all(cfg.get(k) is False for k in (
                'real_data_execution_permitted', 'model_fitting_permitted',
                'holdout_scoring_permitted', 'clinical_use_permitted',
                'public_export_permitted')), 'A blueprint does not authorize real-data work')
    require(cfg.get('source_task') == v26.get('task') and
            cfg.get('source_task') in ('classification', 'regression'),
            'Do not relabel original NHANES classification study as survival')
    require(cfg.get('specialist_demo_tasks') == list(TASKS),
            'Required restricted specialist task inventory')
    require(cfg.get('split_policy') == 'person_disjoint' and
            recipe.get('split_review') == 'person_disjoint',
            'First specialist prototype requires participant-disjoint validation')
    require(type(cfg.get('n_splits')) is int and 2 <= cfg['n_splits'] <= 5,
            'Unsupported number of folds')
    require(type(cfg.get('random_seed')) is int and 0 <= cfg['random_seed'] < 2**32,
            'Invalid seed')
    require(cfg.get('survival') == {
        'censoring': 'right', 'time_origin': 'prediction_index',
        'competing_events': 'unsupported', 'cox_ties': 'breslow',
        'censoring_brier': 'training_ipcw'},
        'Survival task/assumptions must be explicit; competing risks unsupported')
    require(cfg.get('longitudinal') == {
        'target': 'next_observed_visit_value', 'input_window': 'index_visit_only',
        'prediction_horizon': 'variable_next_observed_visit',
        'dropout_model': 'not_implemented'},
        'Variable next-visit outcomes are not fixed-horizon predictions')
    require(cfg.get('selection_rule') == 'synthetic_development_only' and
            cfg.get('independent_holdout') == 'not_accessed',
            'Cannot present exploratory CV as independent evidence')
    return cfg


def make_plan(cfg):
    return dict(schema=REPORT_SCHEMA, case_id=cfg['case_id'],
                config_sha256=digest(cfg), route='BLOCKED_FOR_NEW_ANALYSIS',
                original_task=cfg['source_task'], specialized_demos=cfg['specialist_demo_tasks'],
                horizon=cfg['longitudinal']['prediction_horizon'],
                holdout_history=cfg['holdout_history'],
                index_status=cfg['prediction_index_status'],
                synthetic_only=True, no_participant_tables_opened=True,
                no_models_fitted=True, no_predictions_generated=True,
                no_holdout_targets_accessed=True, public_export=False,
                limitations=[
                    'The NHANES study remains binary classification; no new survival endpoint is established.',
                    'Cox proportional hazards assumes PH and independent noninformative right censoring; checks remain incomplete.',
                    'IPCW assumes independent censoring and usable censoring support; these assumptions are not certified.',
                    'Harrell C can be censoring-dependent; demonstrations are exploratory, not external validation.',
                    'Next observed visit is a variable horizon and can have informative visit schedules/dropout.',
                    'No competing-risk, dynamic landmark, fixed-horizon longitudinal, survey design, or clinical authorization.',
                    'Previously inspected NHANES later-cycle outcomes are not an untouched external test set.'])


def _synthetic_execution_contract(cfg):
    require(isinstance(cfg,dict) and cfg.get('schema')==SCHEMA and
            cfg.get('scope')=='synthetic_only_blueprint' and
            cfg.get('specialist_demo_tasks')==list(TASKS) and
            cfg.get('split_policy')=='person_disjoint' and
            cfg.get('independent_holdout')=='not_accessed' and
            type(cfg.get('n_splits')) is int and 2<=cfg['n_splits']<=5 and
            all(cfg.get(key) is False for key in (
                'real_data_execution_permitted','model_fitting_permitted',
                'holdout_scoring_permitted','clinical_use_permitted',
                'public_export_permitted')),
            'Synthetic-only specialist execution contract is invalid')


def _numeric_1d(value, n, what, *, positive=False, binary=False):
    z = np.asarray(value)
    require(z.ndim == 1 and len(z) == n and z.dtype.kind in 'iuf' and
            np.isfinite(z).all(), 'Invalid numeric '+what)
    if positive:
        require(np.all(z > 0), what+' must be strictly positive')
    if binary:
        require(set(z.tolist()) <= {0, 1}, what+' must be binary 0/1')
    return z.astype(int if binary else float)


def _feature_frame(frame, recipe):
    require(isinstance(frame, pd.DataFrame) and frame.columns.is_unique and
            len(frame) > 0 and set(frame.columns) == set(expected_columns(recipe)),
            'Exact canonical features and statuses required, no targets/IDs/times')


def _groups(n, ids, groups):
    require(ids is not None and groups is not None and len(ids) == len(groups) == n,
            'Row IDs and participant groups required outside predictors')
    require(all(pd.notna(x) for x in list(ids)+list(groups)) and
            len(set(ids)) == n, 'Missing or duplicate row IDs')
    require(len(set(groups)) >= 2, 'Need at least two distinct participants')


def _folds(n, ids, groups, k):
    from sklearn.model_selection import GroupKFold
    from ml.case_foldsafe_v25 import validate_partition
    require(len(set(groups)) >= k, 'Too few participants for grouped CV')
    folds = list(GroupKFold(n_splits=k).split(np.zeros(n), groups=groups))
    for tr, va in folds:
        require(len(tr) >= 3 and len(va) >= 2, 'Too few rows per fold')
        validate_partition([ids[i] for i in tr], [ids[i] for i in va],
            policy='person_disjoint', train_groups=[groups[i] for i in tr],
            valid_groups=[groups[i] for i in va])
    return folds


def _km(times, events):
    """Right-continuous Kaplan-Meier; event=1 denotes event for THIS estimator."""
    t = np.asarray(times, dtype=float)
    e = np.asarray(events, dtype=int)
    require(len(t) > 0 and np.isfinite(t).all() and (t > 0).all() and
            set(e.tolist()) <= {0, 1}, 'Invalid Kaplan-Meier inputs')
    steps = []
    survive = 1.0
    for point in np.unique(t[e == 1]):
        at_risk = int(np.sum(t >= point))
        count = int(np.sum((t == point) & (e == 1)))
        survive *= 1.0-count/at_risk
        steps.append((float(point), float(survive)))
    return steps


def _km_at(steps, when, *, before=False):
    s = 1.0
    for t, value in steps:
        if t < when or (not before and t <= when):
            s = value
        else:
            break
    return float(s)


def _cox_fit(Z, times, events, alpha=1.0):
    """Penalized Cox partial likelihood (Breslow ties) and baseline hazard.

    Research-education prototype: assumes right censoring & proportional hazards.
    """
    from scipy.optimize import minimize
    from scipy.special import logsumexp
    X = np.asarray(Z, dtype=float)
    require(X.ndim == 2 and np.isfinite(X).all() and X.shape[1] > 0,
            'Cox requires finite encoded predictors')
    require(np.sum(events) >= 2 and np.sum(events == 0) >= 1,
            'Cox training must include events and censoring')
    event_times = np.unique(times[events == 1])
    def objective(beta):
        eta = X @ beta
        loss = .5*alpha*np.dot(beta,beta)
        gradient = alpha*beta.copy()
        for tt in event_times:
            at_risk = times >= tt
            deaths = (times == tt) & (events == 1)
            d = int(np.sum(deaths))
            log_denom = logsumexp(eta[at_risk])
            weights = np.exp(eta[at_risk] - log_denom)
            loss += d*log_denom - np.sum(eta[deaths])
            gradient += d*(X[at_risk].T@weights) - np.sum(X[deaths], axis=0)
        return float(loss), gradient
    fit = minimize(objective, np.zeros(X.shape[1]), jac=True, method='L-BFGS-B',
                   options={'maxiter': 400, 'ftol': 1e-9})
    require(fit.success and np.isfinite(fit.x).all(), 'Cox optimizer did not converge')
    beta = fit.x
    eta = X @ beta
    baseline = []
    cumhaz = 0.0
    for tt in event_times:
        d = int(np.sum((times == tt) & (events == 1)))
        # log-space baseline increments avoid overflow/underflow for moderate toy data
        log_denom = logsumexp(eta[times >= tt])
        cumhaz += float(np.exp(np.log(d)-log_denom))
        baseline.append((float(tt),float(cumhaz)))
    return beta,baseline


def _cox_risk(encoded, beta, baseline, horizon):
    cumhaz = 0.0
    for tt, val in baseline:
        if tt <= horizon: cumhaz = val
        else: break
    exp_eta = np.exp(np.clip(np.asarray(encoded) @ beta, -30, 30))
    return -np.expm1(-cumhaz*exp_eta)


def _concordance(times, events, risk):
    # Strict inequality avoids ambiguous ties at same follow-up time.
    total=0
    credit=0.0
    for i in range(len(times)):
        if events[i] != 1: continue
        for j in range(len(times)):
            if times[i] < times[j]:
                total+=1
                credit += float(risk[i] > risk[j]) + .5*float(risk[i] == risk[j])
    require(total > 0, 'No comparable survival pairs in validation')
    return credit/total


def _ipcw_brier(train_time, train_event, test_time, test_event, risk, horizon):
    """IPCW with censoring survival learned solely from training partition."""
    censor_km=_km(train_time, 1-train_event)
    require(_km_at(censor_km,horizon) > 1e-8,
            'Insufficient training censoring support at requested horizon')
    scores=[]
    for t,e,p in zip(test_time,test_event,risk):
        if t <= horizon and e == 0:
            continue  # outcome at horizon unobserved (early censored)
        if t <= horizon and e == 1:
            g=_km_at(censor_km,t,before=True)
            actual=1.0
        else:
            g=_km_at(censor_km,horizon)
            actual=0.0
        require(g>1e-8,'Invalid censoring support for IPCW')
        scores.append((actual-float(p))**2/g)
    require(scores,'No evaluable survival outcomes at this horizon')
    return float(sum(scores)/len(test_time))


def evaluate_synthetic_survival(cfg, recipe, frame, duration, event, *, row_ids,
                                people, horizon, synthetic_fixture=False):
    """Grouped, fold-fitted KM vs penalized Cox at one predeclared horizon."""
    require(synthetic_fixture is True, 'Real-data fitting is not authorized')
    _synthetic_execution_contract(cfg)
    _feature_frame(frame,recipe)
    n=len(frame)
    _groups(n,row_ids,people)
    require(len(set(people))==n, 'Survival baseline requires exactly one row per person')
    dur=_numeric_1d(duration,n,'duration',positive=True)
    ev=_numeric_1d(event,n,'event',binary=True)
    require(type(horizon) in (int,float) and math.isfinite(horizon) and horizon>0,
            'Positive fixed survival horizon required')
    require(np.max(dur)>horizon and np.sum(ev)>0 and np.sum(1-ev)>0,
            'Study lacks follow-up or event/censoring diversity')
    folds=_folds(n,list(row_ids),list(people),cfg['n_splits'])
    # Preflight all outcome/survival support before any fitting.
    for tr, va in folds:
        require(np.sum(ev[tr])>=2 and np.sum(ev[tr]==0)>=1 and
                np.sum(ev[va])>=1 and np.sum(ev[va]==0)>=1 and
                np.max(dur[tr])>horizon and np.max(dur[va])>horizon,
                'Fold lacks events/censoring or follow-up horizon')
        require(_km_at(_km(dur[tr],1-ev[tr]),horizon)>1e-8,
                'Censoring survival vanishes before horizon')
        require(any((ev[i]==1 and dur[i]<dur[j]) for i in va for j in va),
                'Fold has no comparable survival pairs')
    results={'kaplan_meier':[],'penalized_cox':[]}
    for tr,va in folds:
        proc=build_preprocessor(recipe,synthetic_fixture=True)
        Xtrain=proc.fit_transform(frame.iloc[tr]); Xvalid=proc.transform(frame.iloc[va])
        require(np.isfinite(Xtrain).all() and np.isfinite(Xvalid).all(), 'Invalid encoded values')
        baseline_risk=1.0-_km_at(_km(dur[tr],ev[tr]),horizon)
        beta,base=_cox_fit(Xtrain,dur[tr],ev[tr])
        for name,risk in [('kaplan_meier',np.full(len(va),baseline_risk)),
                          ('penalized_cox',_cox_risk(Xvalid,beta,base,horizon))]:
            require(np.isfinite(risk).all() and np.all((risk>=0)&(risk<=1)),
                    'Nonfinite/invalid horizon risk')
            results[name].append({'ipcw_brier':_ipcw_brier(dur[tr],ev[tr],dur[va],ev[va],risk,horizon),
                                  'harrell_c':_concordance(dur[va],ev[va],risk)})
    return {'schema':'FRAILTYSCOPE_SYNTHETIC_SURVIVAL_DEV_V27',
            'task':'right_censored_survival','horizon':float(horizon),
            'folds':len(folds),'n_synthetic_rows':n,
            'results':{name:{key:float(np.mean([r[key] for r in scores])) for key in
                              ('ipcw_brier','harrell_c')} for name,scores in results.items()},
            'development_only':True, 'independent_validation':False,
            'censoring_assumptions_unverified':True,'models_saved':False,
            'predictions_exported':False,'clinical_use_permitted':False}


def _visit_chronology(groups, origin, future, lag, target):
    """Strict sequential visits, next-outcome continuity, no future-visit features."""
    for person in set(groups):
        indices=[i for i,v in enumerate(groups) if v==person]
        indices.sort(key=lambda i: origin[i])
        for ii in indices:
            require(origin[ii] < future[ii], 'Non-forward visit target')
        for a,b in zip(indices,indices[1:]):
            require(origin[a] < origin[b] and future[a]==origin[b] and
                    np.isclose(target[a],lag[b],rtol=0,atol=1e-10),
                    'Non-consecutive visits or future outcome used inconsistently')


def evaluate_synthetic_longitudinal(cfg,recipe,index_features,previous_outcome,
                                     next_outcome, *, row_ids,people,index_times,
                                     target_times,synthetic_fixture=False):
    """Predict next OBSERVED visit from current visit; group-disjoint development CV."""
    require(synthetic_fixture is True,'Real-data fitting is not authorized')
    _synthetic_execution_contract(cfg)
    _feature_frame(index_features,recipe)
    n=len(index_features)
    _groups(n,row_ids,people)
    lag=_numeric_1d(previous_outcome,n,'previous outcome')
    y=_numeric_1d(next_outcome,n,'next outcome')
    require(index_times is not None and target_times is not None and
            len(index_times)==len(target_times)==n, 'Visit timestamps are required')
    t0=pd.to_datetime(index_times,format='ISO8601',errors='coerce',utc=True)
    t1=pd.to_datetime(target_times,format='ISO8601',errors='coerce',utc=True)
    require(not t0.isna().any() and not t1.isna().any(), 'Invalid visit timestamps')
    _visit_chronology(list(people), t0, t1, lag, y)
    require(len(set(people))>=cfg['n_splits'], 'Not enough independent people')
    folds=_folds(n,list(row_ids),list(people),cfg['n_splits'])
    for tr,va in folds:
        require(np.std(y[tr])>0 and np.std(y[va])>0,
                'Fold outcomes must vary for regression comparison')
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_absolute_error,mean_squared_error
    scores={'last_observation':[],'ridge_with_lag':[]}
    for tr,va in folds:
        pre=build_preprocessor(recipe,synthetic_fixture=True)
        xtr=pre.fit_transform(index_features.iloc[tr])
        xva=pre.transform(index_features.iloc[va])
        Xtr=np.column_stack([xtr,lag[tr]])
        Xva=np.column_stack([xva,lag[va]])
        predictor=make_pipeline(StandardScaler(),Ridge(alpha=1.0))
        predictor.fit(Xtr,y[tr])
        for name,prediction in [('last_observation',lag[va]),
                                ('ridge_with_lag',predictor.predict(Xva))]:
            require(np.isfinite(prediction).all(),'Invalid longitudinal predictions')
            scores[name].append({'mae':float(mean_absolute_error(y[va],prediction)),
                                 'rmse':float(np.sqrt(mean_squared_error(y[va],prediction)))})
    return {'schema':'FRAILTYSCOPE_SYNTHETIC_NEXT_VISIT_DEV_V27',
            'task':'next_observed_visit_regression','n_synthetic_transitions':n,
            'folds':len(folds),'results':{
                name:{key:float(np.mean([fold[key] for fold in s])) for key in ('mae','rmse')}
                for name,s in scores.items()},
            'variable_horizon':True,'dropout_not_modeled':True,
            'development_only':True,'independent_validation':False,
            'models_saved':False,'predictions_exported':False,'clinical_use_permitted':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan',action='store_true')
    mode.add_argument('--audit',action='store_true')
    p.add_argument('--project',default='.')
    p.add_argument('--config',default='research/cases/nhanes_temporal_v27.json')
    args=p.parse_args()
    root=Path(args.project).resolve()
    cfg=json.loads(local_file(root,args.config,'research').read_text())
    v26=json.loads(local_file(root,cfg['related_v26_protocol'],'research').read_text())
    v25=json.loads(local_file(root,v26['related_v25_protocol'],'research').read_text())
    from ml.case_dictionary_timing_v23 import validate_protocol as check23
    from ml.case_governance_v22 import validate_protocol as check22
    from ml.case_harmonization_v24 import validate_protocol as check24
    from ml.case_foldsafe_v25 import validate_recipe
    from ml.case_task_models_v26 import validate_design as check26,digest as digest26
    v23=json.loads(local_file(root,v25['related_v23_protocol'],'research').read_text())
    v24=json.loads(local_file(root,v25['related_v24_protocol'],'research').read_text())
    v22=json.loads(local_file(root,v23['related_v22_protocol'],'research').read_text())
    manifest=json.loads(local_file(root,v23['case_manifest'],'research').read_text())
    check22(v22);check23(v23,manifest,v22);check24(v24,v23)
    validate_recipe(v25,v23,v24);check26(v26,v25,manifest)
    validate_design(cfg,v26,v25)
    result=make_plan(cfg)
    if args.audit:
        prior=local_file(root,cfg['related_private_v26_review'],'artifacts')
        require(prior.suffix=='.json' and prior.stat().st_size<250_000,
                'Unsafe previous private metadata report')
        obj=json.loads(prior.read_text())
        require(obj.get('schema')=='FRAILTYSCOPE_PRIVATE_TASK_MODEL_REVIEW_V26' and
                obj.get('config_sha256')==digest26(v26) and obj.get('case_id')==cfg['case_id'] and
                obj.get('v25_private_metadata_verified') is True and
                obj.get('route')=='BLOCKED_FOR_NEW_ANALYSIS' and
                obj.get('no_participant_tables_opened') is True and
                obj.get('no_models_fitted') is True and obj.get('no_predictions_generated') is True and
                obj.get('no_holdout_targets_accessed') is True and obj.get('public_export') is False,
                'Previous private v0.26 review metadata invalid')
        result['v26_private_metadata_verified']=True
    print('V27 TEMPORAL SPECIALIST PLAN:',json.dumps({k:result[k] for k in
          ('case_id','route','original_task','specialized_demos','horizon',
           'holdout_history','index_status')},indent=2))
    if args.audit:
        target=(root/'artifacts/cases'/cfg['case_id']/'temporal_v27'/
                digest(cfg)[:12]/'temporal_review.json').resolve()
        require(target.is_relative_to((root/'artifacts/cases').resolve()) and
                not target.exists(),'Immutable private v0.27 review already exists')
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x') as f:
            json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
        print('PRIVATE IMMUTABLE METADATA REVIEW:',target)
    else:
        print('PLAN ONLY. Source contracts checked; no private artifact opened.')
    print('No participant records, research labels, model fits, holdout outcomes or predictions accessed.')

if __name__=='__main__': main()
