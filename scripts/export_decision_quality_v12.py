"""Explicit allowlisted export of verified NHANES aggregate decision diagnostics."""
from __future__ import annotations
import json,math
from pathlib import Path

PROVENANCE='REAL_NHANES_AGGREGATE_ONLY'
SCHEMA='FRAILTYSCOPE_PUBLIC_DECISION_QUALITY_V12'


def ensure_numeric_tree(v):
    if isinstance(v,dict):
        for k,z in v.items():
            if len(str(k))>80:raise ValueError('Oversize key')
            ensure_numeric_tree(z)
    elif isinstance(v,list):
        if len(v)>120:raise ValueError('Oversize array')
        for z in v:ensure_numeric_tree(z)
    elif isinstance(v,(int,float)) and not isinstance(v,bool):
        if not math.isfinite(v):raise ValueError('Non-finite number')
    elif isinstance(v,str):
        if len(v)>450:raise ValueError('Oversize string')
    elif not (v is None or isinstance(v,bool)):raise ValueError('Unsupported JSON value')


def clean(local,meta,audit):
    if local.get('schema')!='FRAILTYSCOPE_LOCAL_DECISION_QUALITY_V12':raise ValueError('Wrong research report')
    if local.get('case_id')!='nhanes_mortality_v10' or meta.get('dataset_sha256')!=local.get('dataset_sha256'):
        raise ValueError('Refuse unmatched case/data fingerprint')
    if audit.get('provenance')!=PROVENANCE or audit.get('schema')!='FRAILTYSCOPE_PUBLIC_CASE_AUDIT_V11':
        raise ValueError('Prior NHANES aggregate audit required')
    ct=local['counts']
    if ct!={'validation':292,'evaluation':1257,'events':246}:raise ValueError('NHANES cohort changed; new review required')
    if audit['counts']['evaluation']!=1257:raise ValueError('Prior audit cohort mismatch')
    if local['selected_model']!=meta['selected_model'] or local['evaluation']['confusion']!=meta['evaluation']['confusion']:
        raise ValueError('Final model or confusion changed')
    if abs(local['evaluation']['roc_auc']-meta['evaluation']['roc_auc'])>0.000005:
        raise ValueError('Changed ROC-AUC')
    if abs(local['evaluation']['brier']-meta['evaluation']['brier'])>0.000005:
        raise ValueError('Changed Brier score')
    if abs(local['selection_threshold_from_validation']-meta['selected_threshold'])>1e-9:
        raise ValueError('Threshold changed')
    if len(local['threshold_diagnostics_descriptive_only'])!=14:raise ValueError('Expected 14 fixed threshold diagnostics')
    # Construct every public field explicitly. Do not export filenames, IDs, hashes, scores, or feature rows.
    out={'provenance':PROVENANCE,'schema':SCHEMA,
        'study':'NHANES 2011–2014; linked mortality public-use 2019',
        'endpoint':'Exploratory approximately five-year all-cause mortality',
        'model':local['selected_model'],'counts':dict(ct),
        'locked_threshold':local['selection_threshold_from_validation'],
        'validation_reference':{k:local['validation_reference'][k] for k in ('roc_auc','brier','precision','recall')},
        'evaluation':{k:local['evaluation'][k] for k in ('roc_auc','average_precision','brier','precision','recall','specificity','false_positive_rate','confusion')},
        'thresholds':[], 'uncertainty':{'method':local['uncertainty']['method'],
               'replicates':local['uncertainty']['replicates'], 'interval_type':'95% percentile','intervals':[]},
        'overall_calibration':{k:local['overall_calibration'][k] for k in ('n','events','observed_event_rate','mean_predicted_risk','observed_minus_predicted','brier')},
        'subgroups':[],'calibration_bands':[],
        'experiments':None,'limitations':list(local['limitations'])}
    for z in local['threshold_diagnostics_descriptive_only']:
        out['thresholds'].append({k:z[k] for k in ('threshold','recall','precision','false_positive_rate','f2',
                'net_benefit','treat_all_net_benefit','treat_none_net_benefit','predicted_positive')})
        if z['predicted_positive']<0 or z['predicted_positive']>ct['evaluation']:
            raise ValueError('Invalid predicted positive count')
    for z in local['uncertainty']['intervals']:
        d={k:z[k] for k in ('metric','estimate','lower','upper')}
        if not 0<=d['lower']<=d['upper']<=1:raise ValueError('Invalid confidence interval')
        out['uncertainty']['intervals'].append(d)
    for z in local['subgroups']:
        if z['n']<100 or min(z['events'],z['n']-z['events'])<20:
            raise ValueError('Undersized subgroup')
        out['subgroups'].append({k:z[k] for k in ('dimension','group','n','events','roc_auc','brier',
            'recall','false_positive_rate','mean_predicted_risk','observed_event_rate','observed_minus_predicted')})
    for z in local['subgroup_calibration']:
        if z['n']<50 or min(z['events'],z['n']-z['events'])<10:raise ValueError('Undersized calibration band')
        out['calibration_bands'].append({k:z[k] for k in ('dimension','group','band','n','events',
             'mean_predicted_risk','observed_event_rate')})
    cmp=local.get('experiment_comparison')
    if cmp:
        if cmp['comparison_type']!='DESCRIPTIVE_AGGREGATE_ONLY_NOT_PAIRED' or len(cmp['rows'])!=3:
            raise ValueError('Unexpected comparison form')
        out['experiments']={'comparison_type':cmp['comparison_type'],'rows':[],
            'limitation':cmp['limitation']}
        for z in cmp['rows']:
            if z['n']!=1257 or z['events']!=246:raise ValueError('Incompatible experiment counts')
            out['experiments']['rows'].append({k:z[k] for k in ('experiment','n','events',
                'roc_auc','brier','average_precision','recall','precision','false_positives','threshold')})
    forbidden={'seqn','patient_id','person_id','source_sha256','dataset_sha256','predictions','scores',
               'individual_rows','individual_scores','raw_predictions','case_ids','local_examples'}
    def walk(node):
        if isinstance(node,dict):
            if forbidden.intersection({str(k).lower() for k in node}):raise ValueError('Protected field in public output')
            for v in node.values():walk(v)
        if isinstance(node,list):
            for v in node:walk(v)
    walk(out);ensure_numeric_tree(out)
    b=json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False).encode('utf-8')
    if len(b)>75_000:raise ValueError('Public payload unexpectedly large')
    return out


def export(root:Path):
    base=root/'artifacts/cases/nhanes_mortality_v10'
    j=lambda p:json.loads(p.read_text())
    result=clean(j(base/'decision_quality_v12_local.json'), j(base/'metrics.json'),
                  j(root/'web/public/data/nhanes-case-audit-v11.json'))
    target=root/'web/public/data/nhanes-decision-quality-v12.json'
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    print('APPROVED REAL AGGREGATE:',target,'thresholds',len(result['thresholds']),
          'subgroups',len(result['subgroups']))
    return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--project',default='.');a=p.parse_args()
    export(Path(a.project).resolve())
