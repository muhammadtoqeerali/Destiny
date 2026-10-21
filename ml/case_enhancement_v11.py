"""Predeclared calibration experiment: validation-only cross-fit Platt scaling.

No evaluation-data selection. Selected enhancement can be rejected; never promise
improvement. Fitted calibration and respondent scores remain local.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import joblib
from ml.case_model_io_v11 import load_canonical_trusted_model
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from ml.case_engine_v10 import validate_manifest,load_data,split_data,calculate_metrics,selected_threshold

def logit(probs):
    p=np.clip(np.asarray(probs,float),1e-5,1-1e-5)
    if not np.isfinite(p).all():raise ValueError('Probabilities must be finite')
    return np.log(p/(1-p)).reshape(-1,1)

def crossfit_calibration(y,probs,folds=3):
    y=np.asarray(y,int);p=np.asarray(probs,float)
    if len(y)!=len(p) or min(np.bincount(y,minlength=2))<folds:
        raise ValueError('Insufficient class counts for cross-fitting')
    scores=logit(p);oof=np.full(len(y),np.nan)
    sk=StratifiedKFold(n_splits=folds,shuffle=True,random_state=2026)
    for train,valid in sk.split(scores,y):
        lr=LogisticRegression(C=1.0,max_iter=400,random_state=2026)
        lr.fit(scores[train],y[train]);oof[valid]=lr.predict_proba(scores[valid])[:,1]
    if not np.isfinite(oof).all():raise ValueError('OOF calibration incomplete')
    return oof

def choose_calibration(y,raw,oof,min_improvement=0.002):
    """Rule fixed in advance; compare OOF Brier and discriminative performance."""
    y=np.asarray(y,int);raw=np.asarray(raw,float);oof=np.asarray(oof,float)
    raw_b=float(brier_score_loss(y,raw));cal_b=float(brier_score_loss(y,oof))
    raw_auc=float(roc_auc_score(y,raw));cal_auc=float(roc_auc_score(y,oof))
    approved=(raw_b-cal_b>=min_improvement and cal_auc>=raw_auc-0.015)
    return {'accepted':bool(approved),'required_min_brier_gain':min_improvement,
            'raw_validation_brier':round(raw_b,6),'crossfit_calibrated_brier':round(cal_b,6),
            'oof_brier_gain':round(raw_b-cal_b,6),
            'raw_validation_auc':round(raw_auc,6),'crossfit_calibrated_auc':round(cal_auc,6),
            'decision':'Cross-fitted validation Brier improvement and AUC noninferiority; evaluation unseen'}

def generate(project:Path,spec:dict):
    validate_manifest(spec)
    if spec['task']!='classification':raise ValueError('Platt calibration only applies to classification')
    frame,y,sha=load_data(project,spec);tr,va,te=split_data(frame,y,spec)
    out=project/'artifacts'/'cases'/spec['case_id']
    metrics=json.loads((out/'metrics.json').read_text())
    if metrics.get('dataset_sha256')!=sha:raise ValueError('Mismatch: case run must use current dataset')
    model=load_canonical_trusted_model(out/'best_model.joblib')  # local trusted artifacts only
    cols=spec['features']['numeric']+spec['features']['categorical']
    val_raw=model.predict_proba(frame.iloc[va][cols])[:,1]
    y_val=np.asarray(y.iloc[va],int)
    val_oof=crossfit_calibration(y_val,val_raw)
    decision=choose_calibration(y_val,val_raw,val_oof)
    calibrator=LogisticRegression(C=1.0,max_iter=400,random_state=2026).fit(logit(val_raw),y_val)
    # Threshold chosen on original validation raw probabilities, not on evaluation.
    original_t=float(metrics['selected_threshold'])
    # For accepted calibration threshold choice, use cross-fitted validation estimates.
    accepted_t=selected_threshold(y_val,val_oof)
    y_test=np.asarray(y.iloc[te],int)
    raw_test=model.predict_proba(frame.iloc[te][cols])[:,1]
    expected=calculate_metrics('classification',y_test,raw_test,raw_test,original_t)
    for metric in ('roc_auc','brier','recall','precision'):
        if abs(expected[metric]-metrics['evaluation'][metric])>0.002:
            raise ValueError('Saved model predictions differ from existing benchmark: '+metric)
    if expected['confusion']!=metrics['evaluation']['confusion']:
        raise ValueError('Saved model disagrees with confusion matrix')
    cal_test=calibrator.predict_proba(logit(raw_test))[:,1]
    chosen=cal_test if decision['accepted'] else raw_test
    chosen_t=accepted_t if decision['accepted'] else original_t
    result={'schema':'FRAILTYSCOPE_ENHANCEMENT_V11','report_type':'LOCAL_AGGREGATE_RESEARCH_ONLY',
        'case_id':spec['case_id'],'dataset_sha256':sha,'method':'Validation-only cross-fitted Platt recalibration',
        'model':metrics['selected_model'],'rule':decision,
        'thresholds':{'original':round(original_t,4),'calibrated_oof_f2':round(accepted_t,4),'selected':round(float(chosen_t),4)},
        'later_cycle':{'original':calculate_metrics('classification',y_test,raw_test,raw_test,original_t),
                       'selected':calculate_metrics('classification',y_test,chosen,chosen,chosen_t)},
        'review_notes':['Enhancement selected solely by cross-fitted development-validation criteria.',
          'Validation cases previously used for choosing base model; further external study is required.',
          'Later-cycle scores report evaluation only; never select enhancement using evaluation outcomes.',
          'Results exploratory, unweighted, not a clinical threshold or calibrated patient prognosis.']}
    if decision['accepted']:joblib.dump(calibrator,out/'platt_calibrator_v11.joblib')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',default='research/cases/nhanes_mortality_v10.json');p.add_argument('--project',default='.');a=p.parse_args()
    project=Path(a.project).resolve();cfg=(project/a.config).resolve()
    if not cfg.is_relative_to(project):raise ValueError('Config must stay in project')
    spec=json.loads(cfg.read_text());report=generate(project,spec)
    dest=project/'artifacts'/'cases'/spec['case_id']/'enhancement_v11_local.json'
    dest.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('LOCAL ENHANCEMENT CHECK:',json.dumps({'accepted':report['rule']['accepted'],
      'oof_brier_gain':report['rule']['oof_brier_gain'],'later_cycle':report['later_cycle']},indent=2))
    print('No fitted calibration coefficients, per-person scores or records published.')
if __name__=='__main__':main()
