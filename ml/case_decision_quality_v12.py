"""Split-locked diagnostic evaluation of an ALREADY fitted local classifier.

No training or tuning. All participant scores remain ephemeral, never exported.
The public report is produced separately with an explicit aggregate allowlist.
Simple IID bootstrap is exploratory, NOT NHANES complex-survey inference.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from ml.case_engine_v10 import validate_manifest, load_data, split_data
from ml.case_model_io_v11 import load_canonical_trusted_model

SCHEMA='FRAILTYSCOPE_LOCAL_DECISION_QUALITY_V12'
THRESHOLDS=(0.05,0.08,0.10,0.12,0.15,0.17,0.20,0.22,0.25,0.30,0.35,0.40,0.45,0.50)


def checked(y, p):
    y=np.asarray(y,dtype=int).reshape(-1)
    p=np.asarray(p,dtype=float).reshape(-1)
    if len(y)!=len(p) or len(y)<10 or not set(y).issubset({0,1}) or len(set(y))<2:
        raise ValueError('Require matching binary observations with both outcomes')
    if not np.isfinite(p).all() or ((p<0)|(p>1)).any():
        raise ValueError('Invalid probabilities')
    return y,p


def confusion(y,p,threshold):
    if not 0<threshold<1: raise ValueError('Threshold must be strictly between zero and one')
    y,p=checked(y,p)
    pred=p>=threshold
    return {'tn':int(((y==0)&~pred).sum()),'fp':int(((y==0)&pred).sum()),
            'fn':int(((y==1)&~pred).sum()),'tp':int(((y==1)&pred).sum())}


def metric(y,p,threshold):
    y,p=checked(y,p)
    c=confusion(y,p,threshold)
    tp,fn,tn,fp=c['tp'],c['fn'],c['tn'],c['fp']
    prec=tp/(tp+fp) if tp+fp else 0.
    recall=tp/(tp+fn)
    specificity=tn/(tn+fp)
    f2=5*prec*recall/(4*prec+recall) if 4*prec+recall else 0.
    # Decision-curve net benefit is meaningful ONLY under the stated threshold-risk trade-off.
    return {'threshold':round(float(threshold),4),'n':len(y),'events':int(y.sum()),
            'roc_auc':round(float(roc_auc_score(y,p)),6),
            'average_precision':round(float(average_precision_score(y,p)),6),
            'brier':round(float(brier_score_loss(y,p)),6),
            'precision':round(prec,6),'recall':round(recall,6),'specificity':round(specificity,6),
            'false_positive_rate':round(1-specificity,6),'f2':round(f2,6),'confusion':c}


def threshold_curve(y,p,thresholds=THRESHOLDS):
    y,p=checked(y,p)
    out=[];n=len(y);events=int(y.sum())
    for t in thresholds:
        c=confusion(y,p,float(t))
        d=metric(y,p,float(t))
        odds=t/(1-t)
        # Treat-all is conditional on the same population and cost-ratio assumption.
        nb=c['tp']/n-c['fp']/n*odds
        all_nb=events/n-(n-events)/n*odds
        out.append({'threshold':round(float(t),4),'recall':d['recall'],
                    'precision':d['precision'],'false_positive_rate':d['false_positive_rate'],
                    'specificity':d['specificity'],'f2':d['f2'],
                    'net_benefit':round(nb,6),'treat_all_net_benefit':round(all_nb,6),
                    'treat_none_net_benefit':0.,'predicted_positive':c['tp']+c['fp']})
    return out


def calibration_summary(y,p):
    y,p=checked(y,p)
    return {'n':len(y),'events':int(y.sum()),'observed_event_rate':round(float(y.mean()),6),
            'mean_predicted_risk':round(float(p.mean()),6),
            'observed_minus_predicted':round(float(y.mean()-p.mean()),6),
            'brier':round(float(brier_score_loss(y,p)),6)}


def subgroup_report(y,p,groups,threshold,min_n=100,min_events=20):
    y,p=checked(y,p)
    if len(groups)!=len(y):raise ValueError('Group alignment error')
    a=np.asarray(groups,dtype=object)
    out=[]
    for group in dict.fromkeys(a.tolist()):
        if group is None or pd.isna(group):continue
        mask=a==group
        n=int(mask.sum());e=int(y[mask].sum())
        if n<min_n or min(e,n-e)<min_events:continue
        m=metric(y[mask],p[mask],threshold)
        # Avoid exact single-respondent or small subgroup disclosure.
        out.append({'group':str(group)[:64], 'n':n,'events':e,
            'roc_auc':m['roc_auc'],'brier':m['brier'],'recall':m['recall'],
            'false_positive_rate':m['false_positive_rate'],
            'mean_predicted_risk':calibration_summary(y[mask],p[mask])['mean_predicted_risk'],
            'observed_event_rate':round(e/n,6),
            'observed_minus_predicted':round(float(y[mask].mean()-p[mask].mean()),6)})
    return out


def group_calibration_bins(y,p,groups,bins=3,min_n=50,min_events=10):
    """Within-group quantile risk bands; suppress bins with small event/non-event cells.

    Bins are descriptive, not used to fit, recalibrate or select the model.
    """
    y,p=checked(y,p)
    if len(groups)!=len(y):raise ValueError('Group alignment error')
    arr=np.asarray(groups,dtype=object);out=[]
    for group in dict.fromkeys(arr.tolist()):
        if group is None or pd.isna(group):continue
        idx=np.flatnonzero(arr==group)
        if len(idx)<bins*min_n:continue
        # Tie-safe deterministic allocation by score rank; never expose indices.
        order=idx[np.argsort(p[idx],kind='mergesort')]
        for j,piece in enumerate(np.array_split(order,bins),1):
            n=len(piece);e=int(y[piece].sum())
            if n<min_n or min(e,n-e)<min_events:continue
            out.append({'group':str(group)[:64], 'band':j, 'n':n, 'events':e,
                        'mean_predicted_risk':round(float(p[piece].mean()),6),
                        'observed_event_rate':round(e/n,6)})
    return out


def bootstrap_intervals(y,p,threshold,draws=500,seed=2026):
    """IID percentile intervals only, no false survey-design confidence claims."""
    y,p=checked(y,p)
    if not isinstance(draws,int) or not 100<=draws<=5000:raise ValueError('Bootstrap draws outside supported limits')
    n=len(y);rng=np.random.default_rng(seed)
    draws_out={k:[] for k in ('roc_auc','brier','recall','false_positive_rate','average_precision')}
    for _ in range(draws):
        z=rng.integers(0,n,size=n)
        if len(set(y[z]))<2:continue
        sample=metric(y[z],p[z],threshold)
        for k in draws_out:draws_out[k].append(sample[k])
    if min(map(len,draws_out.values()))<0.95*draws:raise ValueError('Too many single-class bootstrap samples')
    return {'method':'Exploratory participant-IID percentile bootstrap; ignores NHANES strata, clusters and weights',
       'replicates':draws,'interval_type':'95% percentile','intervals':[
         {'metric':key,'estimate':metric(y,p,threshold)[key],
          'lower':round(float(np.quantile(vals,0.025)),6),'upper':round(float(np.quantile(vals,0.975)),6)}
          for key,vals in draws_out.items()]}


def age_groups(series):
    vals=pd.to_numeric(pd.Series(series),errors='coerce')
    out=np.full(len(vals),None,dtype=object)
    for label,lo,hi in [('65–69',65,69),('70–74',70,74),('75–79',75,79),('80+',80,120)]:
        out[vals.between(lo,hi).fillna(False).to_numpy()]=label
    return out


def compare_reports(case_metric, specialist, refined, count, events):
    """Compare THREE existing aggregate formats without training or test-set selection.

    The public v0.8 baseline uses ``testAtF2`` and ``threshold``; the v0.8.1
    refinement uses ``test`` and ``selectedThreshold``; the v0.10 local case
    report uses ``evaluation`` and ``selected_threshold``. Never infer a
    threshold from classification results or silently substitute the 0.50 run.
    """
    import math
    expected=int(count)
    event_count=int(events)
    sources=(
        ('General-purpose CatBoost',case_metric,'evaluation','selected_threshold',True),
        ('Specialist CatBoost',specialist,'testAtF2','threshold',False),
        ('Specialist Histogram Boosting',refined,'test','selectedThreshold',False),
    )
    rows=[]
    for name, report, metrics_key, threshold_key, general in sources:
        if not isinstance(report,dict) or not isinstance(report.get(metrics_key),dict):
            raise ValueError(f'{name}: expected aggregate metric field {metrics_key!r}')
        m=report[metrics_key]
        if not isinstance(m.get('confusion'),dict):
            raise ValueError(f'{name}: missing aggregate confusion matrix')
        cm=m['confusion']
        if not all(isinstance(cm.get(k),int) and not isinstance(cm[k],bool) and cm[k]>=0
                   for k in ('tn','fp','fn','tp')):
            raise ValueError(f'{name}: invalid confusion counts')
        n_cm=sum(cm[k] for k in ('tn','fp','fn','tp'))
        observed_events=cm['tp']+cm['fn']
        if general:
            partitions=report.get('partition_counts',{})
            actual=partitions.get('test',partitions.get('evaluation',m.get('n')))
        else:
            counts=report.get('counts',{})
            actual=counts.get('test')
            if counts.get('test_events')!=observed_events:
                raise ValueError(f'{name}: published event count disagrees with confusion matrix')
        if (actual!=expected or n_cm!=expected or observed_events!=event_count
                or ('n' in m and m['n']!=expected)):
            raise ValueError(f'{name}: different cohort size or observed outcome events')
        threshold=report.get(threshold_key)
        if not isinstance(threshold,(int,float)) or isinstance(threshold,bool) or not math.isfinite(threshold) or not 0<threshold<1:
            raise ValueError(f'{name}: missing or invalid selected threshold {threshold_key!r}')
        for k in ('roc_auc','brier','average_precision','recall','precision'):
            value=m.get(k)
            if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or not 0<=value<=1:
                raise ValueError(f'{name}: invalid evaluation metric {k!r}')
        rows.append({'experiment':name,'n':expected,'events':event_count,
           'roc_auc':m['roc_auc'],'brier':m['brier'],'average_precision':m['average_precision'],
           'recall':m['recall'],'precision':m['precision'],
           'false_positives':cm['fp'],'threshold':float(threshold)})
    return {'comparison_type':'DESCRIPTIVE_AGGREGATE_ONLY_NOT_PAIRED',
      'rows':rows,
      'limitation':'Published aggregate metrics cannot establish paired differences; protocols/model tuning differ, and the later cycle was previously inspected. No model is selected using this comparison.'}


def run(project:Path, spec:dict, draws=500):
    validate_manifest(spec)
    if spec['task']!='classification':raise ValueError('Binary classification only; regression/survival require other evaluation contracts')
    frame,y,sha=load_data(project,spec)
    tr,va,te=split_data(frame,y,spec)
    root=project/'artifacts'/'cases'/spec['case_id'];report=json.loads((root/'metrics.json').read_text())
    if report.get('dataset_sha256')!=sha:raise ValueError('Dataset fingerprint changed since model fit')
    model=load_canonical_trusted_model(root/'best_model.joblib')
    cols=spec['features']['numeric']+spec['features']['categorical']
    yv=y.iloc[va].to_numpy(int);yt=y.iloc[te].to_numpy(int)
    pv=np.asarray(model.predict_proba(frame.iloc[va][cols])[:,1],float)
    pt=np.asarray(model.predict_proba(frame.iloc[te][cols])[:,1],float)
    t=float(report['selected_threshold'])
    actual=metric(yt,pt,t)
    stored=report['evaluation']
    for k in ('roc_auc','brier','recall','precision','average_precision'):
        if abs(actual[k]-stored[k])>0.000005:raise ValueError('Saved model differs from stored evaluation: '+k)
    if actual['confusion']!=stored['confusion']:raise ValueError('Saved model confusion differs from stored evaluation')
    # The decision threshold is fixed by development validation and is never recalculated here.
    if len(yv)!=report.get('partition_counts',{}).get('validation',len(yv)):
        raise ValueError('Validation cohort count changed')
    a=age_groups(frame.iloc[te]['age']) if 'age' in frame else np.full(len(te),None,dtype=object)
    sex=frame.iloc[te]['sex'].astype('string').fillna('Unknown').tolist() if 'sex' in frame else [None]*len(te)
    groups={'Age':a,'Sex':sex}
    subgroups=[];calibration=[]
    for kind,g in groups.items():
        subgroups.extend([{'dimension':kind,**v} for v in subgroup_report(yt,pt,g,t)])
        calibration.extend([{'dimension':kind,**v} for v in group_calibration_bins(yt,pt,g)])
    generic=report
    specialist=json.loads((project/'web/public/data/nhanes-aggregate.json').read_text())
    refined=json.loads((project/'web/public/data/nhanes-refinement.json').read_text())
    if spec['case_id']=='nhanes_mortality_v10':
        comparison=compare_reports(generic,specialist,refined,len(te),int(yt.sum()))
    else:comparison=None
    return {'schema':SCHEMA,'report_type':'LOCAL_AGGREGATE_ONLY_NO_INDIVIDUAL_SCORES',
       'case_id':spec['case_id'],'dataset_sha256':sha,'selected_model':report['selected_model'],
       'selection_threshold_from_validation':t,'counts':{'validation':len(va),'evaluation':len(te),'events':int(yt.sum())},
       'validation_reference':metric(yv,pv,t),'evaluation':actual,
       'threshold_diagnostics_descriptive_only':threshold_curve(yt,pt),
       'uncertainty':bootstrap_intervals(yt,pt,t,draws),
       'subgroups':subgroups,'subgroup_calibration':calibration,
       'overall_calibration':calibration_summary(yt,pt),'experiment_comparison':comparison,
       'limitations':['Evaluation thresholds are fixed grid diagnostics, never optimized on evaluation outcomes.',
            '0.22 is a development-chosen threshold, not a clinically validated decision threshold.',
            'Simple IID bootstrap intervals ignore NHANES survey weights, clusters and strata.',
            'The later NHANES cycle has been examined in earlier releases, not untouched external validation.',
            'Age 80+ is top-coded, and PHQ-9 responses are questionnaire measurements.',
            'Public-use linked mortality follow-up may be perturbed. Not clinical decision support.']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',default='.')
    p.add_argument('--config',default='research/cases/nhanes_mortality_v10.json')
    p.add_argument('--bootstrap',type=int,default=500)
    a=p.parse_args();project=Path(a.project).resolve();config=(project/a.config).resolve()
    if not config.is_relative_to(project):raise ValueError('Case manifest must be within project')
    spec=json.loads(config.read_text());report=run(project,spec,a.bootstrap)
    folder=project/'artifacts'/'cases'/spec['case_id'];folder.mkdir(parents=True,exist_ok=True)
    dest=folder/'decision_quality_v12_local.json';dest.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    print('LOCAL DECISION QUALITY REPORT:',dest)
    print('Verified original model:',report['selected_model'],'ROC-AUC',report['evaluation']['roc_auc'])
    print('Validation-locked threshold:',report['selection_threshold_from_validation'])
    print('Subgroups:',len(report['subgroups']),'reliability cells:',len(report['subgroup_calibration']))
    print('No fitted models, per-person scores or participant data exported.')
if __name__=='__main__':main()
