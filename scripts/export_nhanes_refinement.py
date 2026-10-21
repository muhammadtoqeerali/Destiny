"""Disclosure-conscious public aggregate payload for FrailtyScope.

Input report was produced by workstation-only refinement over REAL NHANES data.
An explicit allowlist (never copy arbitrary report keys) forbids individual rows,
participant IDs, raw probabilities, model binaries and low-count cells.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

ALLOWED={'Logistic regression','Histogram gradient boosting','XGBoost','CatBoost'}
LABELS={
 'age':'Age (80+ top-coded)','sex':'Sex','bmi':'Body mass index',
 'walking_difficulty':'Walking difficulty','stairs_difficulty':'Stair difficulty',
 'stooping_difficulty':'Stooping difficulty','heart_failure':'Heart failure',
 'coronary_disease':'Coronary disease','stroke':'Stroke','cancer':'Cancer',
 'diabetes':'Diabetes','hypertension':'Hypertension','ever_smoked':'Ever smoked',
 'phq9_score':'PHQ-9 questionnaire score'}
# Permit only the two known wording variants of the same PHQ-9 variable.
# Machine keys and the public label remain canonical and never depend on raw input.
COVERAGE_NAMES = {label: key for key, label in LABELS.items()}
COVERAGE_NAMES['PHQ-9 score'] = 'phq9_score'

def safe(x,name,lower=0,upper=1,digits=4):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or not lower<=x<=upper:
        raise ValueError('Unsafe metric '+name)
    return round(float(x),digits)

def report_to_public(src):
    if src.get('report_type')!='AGGREGATE_NHANES_REFINEMENT_V1' or src.get('data_origin')!='NHANES_PUBLIC_2019_LMF':
        raise ValueError('Refusing non-NHANES or unverified report')
    counts=src['counts']
    for k in ['development','train','validation','test','test_events','total']:
        if not isinstance(counts[k],int) or counts[k]<40:raise ValueError('Invalid count '+k)
    if counts['train']+counts['validation']!=counts['development'] or counts['development']+counts['test']!=counts['total'] or counts['test_events']>=counts['test']:
        raise ValueError('Inconsistent counts')
    if src['selected_model'] not in ALLOWED:raise ValueError('Selected model not allowed')
    if len(src['model_search'])!=4 or {x['model'] for x in src['model_search']}!=ALLOWED:
        raise ValueError('Incomplete four-way comparison')
    models=[]
    for model in src['model_search']:
        v=model['validation']
        models.append({'name':model['model'],'cv_brier':safe(model['cv_brier'],'cv brier'),
           'auc':safe(v['roc_auc'],'validation auc'), 'ap':safe(v['average_precision'],'val AP'),
           'brier':safe(v['brier'],'val Brier'),'trials':int(model['n_trials'])})
    t=src['test_metrics']
    cm=t['confusion']
    if any(not isinstance(cm[k],int) or cm[k]<0 for k in ['tn','fp','fn','tp']):raise ValueError('Bad confusion')
    if sum(cm.values())!=counts['test'] or cm['tp']+cm['fn']!=counts['test_events']:
        raise ValueError('Confusion mismatch')
    vals={k:safe(t[k],k) for k in ['roc_auc','average_precision','brier','accuracy','precision','recall','f1']}
    vals['confusion']={k:int(cm[k]) for k in ['tn','fp','fn','tp']}
    weight=src.get('test_weighted_descriptive')
    weighted={k:safe(weight[k],k) for k in ['roc_auc','average_precision','brier','recall']} if weight else None
    bins=[]
    if len(src['calibration_bins'])!=5:raise ValueError('Expected five calibration groups')
    for x in src['calibration_bins']:
        if x['n']<30:raise ValueError('Small calibration bin')
        bins.append({'group':str(x['group'])[:3],'n':int(x['n']),
                     'predicted':safe(x['predicted'],'cal pred'), 'observed':safe(x['observed'],'cal obs')})
    if sum(x['n'] for x in bins)!=counts['test']:raise ValueError('Incomplete calibration')
    coverage=[]
    if len(src['coverage'])!=len(LABELS):raise ValueError('Unexpected feature count')
    seen=set()
    for x in src['coverage']:
        key=COVERAGE_NAMES.get(x['feature'])
        if key is None:raise ValueError('Unapproved feature: '+str(x['feature']))
        if key in seen:raise ValueError('Duplicate feature: '+key)
        seen.add(key)
        coverage.append({'name':LABELS[key],
                         'observed':safe(x['observed_pct'],'coverage',0,100,1)})
    if seen!=set(LABELS):raise ValueError('Missing approved features')
    ages=[]
    allowed_age={'65–69','70–74','75–79','80+ (top-coded)'}
    if {a['label'] for a in src['age_distribution']}!=allowed_age:raise ValueError('Invalid bins')
    for a in src['age_distribution']:
        if a['count']<20:raise ValueError('Small age bin')
        ages.append({'group':a['label'],'count':int(a['count'])})
    if sum(a['count'] for a in ages)!=counts['total']:raise ValueError('Wrong cohort age total')
    importance=[]
    for x in src['importance']:
        if x['feature'] not in LABELS:raise ValueError('Unexpected importance column')
        importance.append({'name':LABELS[x['feature']],
           'auc_drop':safe(x['auc_drop'],'importance',-1,1)})
    shaps=[]
    if src.get('shap_features'):
        for x in src['shap_features']:
            if x['feature'] not in LABELS:raise ValueError('Unexpected SHAP feature')
            shaps.append({'name':LABELS[x['feature']],
              'mean_abs_shap':safe(x['mean_abs_shap'],'shap',0,1,5)})
    return {
        'provenance':'REAL_NHANES_AGGREGATE_ONLY',
        'analysis':'NHANES · Linked mortality · Model refinement',
        'counts':{k:counts[k] for k in ['development','train','validation','test','test_events','total']},
        'outcome':'Approximately five-year all-cause mortality',
        'selectedModel':src['selected_model'],
        'selectedThreshold':safe(src['selected_threshold'],'cutoff'),
        'models':models,'test':vals,'weightedDescriptive':weighted,
        'ageDistribution':ages,'featureCoverage':coverage,'calibration':bins,
        'featureImportance':importance,'shap':shaps,
        'explanationMethod':'Permutation SHAP of prediction probabilities' if shaps else 'Validation permutation importance',
        'analysisNotes':[
           'US NHANES public-use participants aged 65 years or older.',
           'Public-use follow-up times are perturbed for selected participants; outcome horizon is approximate.',
           'Survey-weighted figures are descriptive; cluster/stratum-based uncertainty is not estimated.',
           'Later-cycle test cohort was already inspected in prior experiments.',
           'No individual participant records or scores are published.'
        ],
    }

def main():
    p=argparse.ArgumentParser();p.add_argument('--report',default='artifacts/realdata_nhanes/refinement.json');p.add_argument('--output',default='web/public/data/nhanes-refinement.json');a=p.parse_args()
    data=report_to_public(json.loads(Path(a.report).read_text()))
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print('PUBLIC AGGREGATE EXPORTED:',dest,'n =',data['counts']['total'])
if __name__=='__main__':main()
