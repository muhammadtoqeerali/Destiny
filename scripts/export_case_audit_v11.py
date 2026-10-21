"""Fail-closed public export from locally reviewed, aggregate forensic case audit."""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path

PROVENANCE='REAL_NHANES_AGGREGATE_ONLY'
MAX_PUBLIC_BYTES=110_000

def verify_number(v,where):
    if v is not None and (not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(float(v))):
        raise ValueError('Invalid numeric value: '+where)

def validate_tree(node,root='payload'):
    if isinstance(node,dict):
        if len(node)>75:raise ValueError('Too many fields in '+root)
        for key,val in node.items():
            if not isinstance(key,str) or len(key)>90:raise ValueError('Bad JSON key')
            validate_tree(val,root+'.'+key)
    elif isinstance(node,list):
        if len(node)>120:raise ValueError('Too many items at '+root)
        for val in node:validate_tree(val,root)
    elif isinstance(node,str):
        if len(node)>250:raise ValueError('Long string, possible unintended data: '+root)
    elif isinstance(node,bool):pass
    elif isinstance(node,(int,float)) or node is None:verify_number(node,root)
    else:raise ValueError('Unsupported JSON type '+root)

def clean(audit,enhancement,source_report,case_metrics):
    if (audit.get('schema')!='FRAILTYSCOPE_CASE_AUDIT_V11' or
        audit.get('case_id')!='nhanes_mortality_v10' or
        audit.get('counts',{}).get('all')!=2422 or audit['counts'].get('evaluation')!=1257):
        raise ValueError('Only audited NHANES cohort allowed for public release')
    if enhancement.get('schema')!='FRAILTYSCOPE_ENHANCEMENT_V11' or enhancement.get('case_id')!=audit['case_id']:
        raise ValueError('Wrong enhancement input')
    if not (audit['source_sha256']==enhancement['dataset_sha256']==case_metrics['dataset_sha256']):
        raise ValueError('Fingerprint mismatch between analyses')
    if source_report['counts']['total']!=audit['counts']['all'] or source_report.get('provenance')!=PROVENANCE:
        raise ValueError('NHANES source provenance mismatch')
    # Only these explicit fields are accepted. No pass-through of unexpected keys.
    result={'provenance':PROVENANCE,'schema':'FRAILTYSCOPE_PUBLIC_CASE_AUDIT_V11',
        'source':'CDC NHANES 2011–2014; linked mortality 2019 public-use',
        'case_id':'nhanes_mortality_v10','counts':audit['counts'],
        'data_contract':{'outcome':'Approximately five-year all-cause mortality','task':'Binary classification',
            'split':'2011–2012 development; 2013–2014 evaluation',
            'model_input_columns':len(audit['feature_profiles']),
            'excluded_from_predictors':['Respondent ID','Survey-cycle split key','Linked mortality timing','Outcome label','Survey sampling weight']},
        'data_integrity':{k:audit['data_integrity'][k] for k in ('phq9_observed_percent','source_check_mismatches','xport_zero_values_normalized','reporting')}
           if 'data_integrity' in audit else None,
        'features':[],'cohort_shift':[],'correlations':[],
        'preprocessing':{'input_feature_count':audit['preprocessing']['input_feature_count'],
            'output_feature_count':audit['preprocessing']['output_feature_count'],'methods':[],
            'quantile_examples':[]},
        'selection':{'metric':audit['selection']['metric'],'model':audit['selection']['model'],
            'candidates':[],'permutation_importance_validation':[],'learning_curve':[]},
        'evaluation':{'metrics':audit['evaluation']['metrics'],
            'baseline':audit['evaluation']['baseline'],'calibration':[],
            'subgroups':[],'observed_prevalence':audit['evaluation'].get('observed_prevalence')},
        'enhancement':{'method':enhancement['method'],'model':enhancement['model'],
            'rule':enhancement['rule'],'thresholds':enhancement['thresholds'],
            'later_cycle':enhancement['later_cycle']},
        'methodology':audit['methodology']}
    for x in audit['feature_profiles']:
        result['features'].append({k:x.get(k) for k in ('feature','label','description','type','observed',
            'missing','missing_pct','unique','summary','iqr_outlier_pct','distribution','distribution_suppressed_n') if k in x})
        if 'distribution' in x and any(p['n']<20 for p in x['distribution']):raise ValueError('Small distribution group')
    result['cohort_shift']=[{k:x[k] for k in ('feature','standardized_mean_difference','development_missing_pct','evaluation_missing_pct')} for x in audit['cohort_shift']]
    result['correlations']=[{k:x[k] for k in ('a','b','spearman_rho')} for x in audit['correlations']]
    for x in audit['preprocessing']['methods']:
        result['preprocessing']['methods'].append({k:x[k] for k in ('feature','label','method','fit_partition','training_missing','validation_missing','after_missing','impute_value','center','scale','observed_training_median','transformed_training_median','before_range','after_range','output_columns') if k in x})
    result['preprocessing']['quantile_examples']=[{k:x[k] for k in ('feature','label','source','before','after')} for x in audit['preprocessing']['quantile_examples']]
    for x in audit['selection']['candidates']:
        result['selection']['candidates'].append({k:x[k] for k in ('name','cv_score','validation','parameters','fit_search_seconds')})
    result['selection']['permutation_importance_validation']=[{k:x[k] for k in ('feature','mean_metric_drop')} for x in audit['selection']['permutation_importance_validation']]
    for x in audit['evaluation'].get('calibration',[]):
        if x['n']<50:raise ValueError('Small calibration cell')
        result['evaluation']['calibration'].append({k:x[k] for k in ('bin','n','predicted','observed')})
    for x in audit['evaluation'].get('subgroups',[]):
        if x['n']<100 or min(x['events'],x['n']-x['events'])<20:
            raise ValueError('Unsafe subgroup')
        result['evaluation']['subgroups'].append({k:x[k] for k in ('group','n','events','event_rate','roc_auc','recall','false_positive_rate','brier')})
    result['selection']['learning_curve']=[{k:x[k] for k in ('train_n','training_brier','validation_brier')} for x in audit['selection'].get('learning_curve',[])]
    # Key-level and serialized-content guards are backups, not a substitute for explicit allowlist.
    forbidden={'SEQN','patient_id','person_id','local_examples','raw','transformed_vector',
        'individual_predictions','participant_rows','date_of_birth','source_sha256','dataset_sha256'}
    def check(node):
        if isinstance(node,dict):
            if forbidden.intersection(node):raise ValueError('Individual content in public output')
            for val in node.values():check(val)
        elif isinstance(node,list):
            for val in node:check(val)
    check(result);validate_tree(result)
    encoded=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False).encode('utf-8')
    if len(encoded)>MAX_PUBLIC_BYTES:raise ValueError('Public payload too large')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--project',default='.');a=p.parse_args();root=Path(a.project).resolve()
    base=root/'artifacts/cases/nhanes_mortality_v10'
    j=lambda path:json.loads(Path(path).read_text())
    approved=clean(j(base/'forensic_audit_v11_local.json'),j(base/'enhancement_v11_local.json'),
         j(root/'web/public/data/nhanes-aggregate.json'),j(base/'metrics.json'))
    dest=root/'web/public/data/nhanes-case-audit-v11.json'
    dest.write_text(json.dumps(approved,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    print('PUBLIC AGGREGATE ONLY:',dest,'features',len(approved['features']), 'calibration bins',len(approved['evaluation']['calibration']))
if __name__=='__main__':main()
