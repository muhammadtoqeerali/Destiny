"""Validate the v0.49 public interview summary against a locally held AGGREGATE-only v0.48 report.

Never reads raw XPT, individual records, predictions or fitted models. Never writes
private report data to GitHub. The deliberately small public summary has a fixed
allowlist of aggregate fields, with no source hashes or participant identifiers.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

SCHEMA = 'FRAILTYSCOPE_INTERVIEW_NHANES_MOBILITY_V49'
CASE = 'public_nhanes_mobility_2015_2018_v48'
ROOT = Path(__file__).resolve().parents[1]
SUMMARY = 'web/app/data/real-mobility-summary-v49.json'
EXPECTED_MODELS = {'CatBoost','Logistic regression','XGBoost','Histogram gradient boosting','Random forest','Dummy prior'}
EXPECTED_FEATURES = {'age','bmi','phq9_score','arthritis','heart_failure','stroke','diabetes','sex'}

class Refused(ValueError):
    pass

def need(condition:bool, reason:str):
    if not condition:raise Refused('INTERVIEW_SUMMARY_REFUSED: '+reason)

def read_public(root:Path)->dict:
    file=root/SUMMARY
    need(file.is_file() and not file.is_symlink(),'Missing or symlinked presentation summary')
    need(file.stat().st_size<24000,'Presentation summary unexpectedly large')
    data=json.loads(file.read_text(encoding='utf8'))
    check_public(data)
    return data

def check_public(d:dict)->None:
    need(type(d) is dict and d.get('schema')==SCHEMA and d.get('case_id')==CASE,'Case/schema mismatch')
    need(d.get('task')=='CROSS_SECTIONAL_CURRENT_MOBILITY_LIMITATION_NOT_FUTURE','Incorrect endpoint')
    need(d.get('source')=='CDC_PUBLIC_USE_NHANES_2015_2018','Incorrect source')
    need(set(d.get('predictors',[]))==EXPECTED_FEATURES and len(d['predictors'])==8,'Predictor inventory changed')
    need(len(d.get('models',[]))==6 and {m.get('name') for m in d['models']}==EXPECTED_MODELS,'Model list changed')
    for m in d['models']:
        for k in ('validation_auc','validation_brier','cv_brier'):
            need(type(m.get(k)) in (float,int) and math.isfinite(m[k]) and 0<=m[k]<=1,'Invalid aggregate score')
    need(d.get('selected_model')=='CatBoost' and min(d['models'],key=lambda m:m['validation_brier'])['name']=='CatBoost','Wrong selection')
    need(d.get('selection_metric')=='LOWEST_VALIDATION_BRIER','Wrong selection rule')
    cohorts=d.get('cohorts',{})
    need(set(cohorts)=={'2015-2016','2017-2018'},'Wrong cohorts')
    for c in cohorts.values():
        need(type(c.get('questionnaire_respondents')) is int and c['questionnaire_respondents']>=100,'Small cohort')
        need(type(c.get('target_events')) is int and 50<=c['target_events']<c['questionnaire_respondents'],'Invalid event count')
        need(abs(c['target_events']/c['questionnaire_respondents']-c['observed_event_fraction'])<2e-5,'Wrong event fraction')
    evaluation=d.get('evaluation',{})
    need(evaluation.get('n')==cohorts['2017-2018']['questionnaire_respondents'] and evaluation.get('events')==cohorts['2017-2018']['target_events'],'Evaluation cohort mismatch')
    for k in ('roc_auc','average_precision','brier','log_loss','sensitivity_at_0_5','specificity_at_0_5'):
        need(type(evaluation.get(k)) in (float,int) and math.isfinite(evaluation[k]) and 0<=evaluation[k]<=1,'Invalid evaluation metric')
    bands=d.get('calibration',[])
    need(len(bands)==3 and all(b['n']>=50 for b in bands),'Unsafe/small calibration band')
    need(sum(b['n'] for b in bands)+d.get('unshown_calibration_n',-1)==evaluation['n'],'Unaccounted calibration respondents')
    need(d['unshown_calibration_n']>=0,'Invalid small-band remainder')
    need(len(d.get('permutation_importance',[]))==8 and {x['feature'] for x in d['permutation_importance']}==EXPECTED_FEATURES,'Importance inventory mismatch')
    need(d.get('phq9_complete',{}).get('2015-2016',0)>=50 and d['phq9_complete'].get('2017-2018',0)>=50,'PHQ coverage mismatch')
    bounds=d.get('boundaries',{})
    for flag in ('clinical_prediction','future_frailty_prediction','h_source','individual_records_exported','survey_design_variance_estimated'):
        need(bounds.get(flag) is False,'Unsafe clinical/prospective claim')
    need(bounds.get('later_cycle_previously_inspected') is True,'Later-cycle inspection history erased')
    raw=json.dumps(d)
    for fragment in ('"SEQN"','"patient_id"','"individual_predictions"','"date_of_birth"','"model_binary"','"HUNT_PARTICIPANT"','"source_sha256"'):
        need(fragment not in raw,'Person-level or private content in public summary')
    need(len(raw)<24000,'Presentation summary exceeds size limit')

def compare(public:dict,private:dict)->None:
    """Cross-check each published number against the private aggregate report; never return its contents."""
    need(private.get('schema')=='FRAILTYSCOPE_PUBLIC_NHANES_MOBILITY_V48' and private.get('case_id')==CASE,'Local aggregate case mismatch')
    need(private.get('clinical_prediction_permitted') is False,'Local aggregate clinical gate changed')
    need(private.get('task')=='CROSS_SECTIONAL_CURRENT_MOBILITY_LIMITATION_NOT_FUTURE','Local outcome changed')
    e=private.get('experiment',{})
    need(e.get('later_cycle_prior_exposure','').startswith('V48_PREVIOUSLY_INSPECTED'),'Prior exposure missing')
    need(e.get('selected_model')==public['selected_model'],'Winner differs')
    need(e.get('feature_availability_contract',{}).get('included_predictors')==public['predictors'],'Local feature inventory differs')
    need(e.get('feature_availability_contract',{}).get('excluded_predictors')==[],'Local feature coverage differs')
    def eq(actual,expected,name):
        need(type(actual) in (float,int) and math.isfinite(actual) and abs(float(actual)-float(expected))<=1.1e-5,'Metric mismatch: '+name)
    for cycle,pub in public['cohorts'].items():
        loc=private['cohorts'][cycle]
        for k in ('questionnaire_respondents','target_events','observed_event_fraction'):
            eq(loc[k],pub[k],cycle+'.'+k)
        eq(loc['phq9_valid_complete_n'],public['phq9_complete'][cycle],cycle+'.phq9_complete')
    loc=e['split']
    for k,v in public['split'].items():eq(loc[k],v,'split.'+k)
    actual={m['model']:m for m in e['model_comparison_development_only']}
    need(set(actual)==EXPECTED_MODELS,'Local model list changed')
    for p in public['models']:
        m=actual[p['name']]
        eq(m['cv_brier'],p['cv_brier'],p['name']+'.CV Brier')
        eq(m['validation']['roc_auc'],p['validation_auc'],p['name']+'.validation AUC')
        eq(m['validation']['brier'],p['validation_brier'],p['name']+'.validation Brier')
        need(m['hyperparameters']==p['hyperparameters'],'Local hyperparameters differ: '+p['name'])
    loc=e['selected_model_later_cycle_test']
    for k,v in public['evaluation'].items():eq(loc[k],v,'evaluation.'+k)
    cal=e['test_calibration_bands_min_n_50']
    need(len(cal)==len(public['calibration']),'Calibration bins mismatch')
    for a,b in zip(cal,public['calibration']):
        for k in ('n','mean_predicted','observed_fraction'):
            eq(a[k],b[k],'calibration.'+k)
        for x,y in zip(a['range'],b['range']):eq(x,y,'calibration.range')
    need(sum(b['n'] for b in cal)+public['unshown_calibration_n']==loc['n'],'Calibration remainder mismatch')
    imp={m['feature']:m for m in e['validation_permutation_importance_delta_brier']}
    need(set(imp)==EXPECTED_FEATURES,'Local feature importance names changed')
    for p in public['permutation_importance']:
        eq(imp[p['feature']]['brier_increase'],p['delta_brier'],'importance.delta_brier')
        eq(imp[p['feature']]['std'],p['std'],'importance.std')
    for metric,values in public['naive_row_bootstrap_95pct'].items():
        for x,y in zip(e['test_naive_row_bootstrap_95pct_not_survey_design_CI'][metric],values):eq(x,y,'CI.'+metric)
    weighted=e['test_survey_weighted_brier_exploratory']
    eq(weighted['n_positive_weights'],public['survey_weighted_brier_exploratory']['n_positive_weights'],'weight.n')
    eq(weighted['brier_exploratory_only'],public['survey_weighted_brier_exploratory']['brier'],'weight.Brier')
    need(weighted['survey_design_variance_not_estimated'] is True,'Survey variance claim changed')

def verify_local(root:Path,path:Path)->None:
    project=root.resolve()
    need(not path.is_symlink() and not path.expanduser().resolve().is_relative_to(project),'Aggregate input must be a non-symlink outside the repository')
    need(path.suffix=='.json' and path.is_file() and 0<path.stat().st_size<300000,'Expected local aggregate-only JSON file')
    public=read_public(root)
    private=json.loads(path.read_text(encoding='utf8'))
    compare(public,private)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--check-public',action='store_true')
    group.add_argument('--verify-local',type=Path,help='Read previously generated aggregate-only JSON outside Git; never raw XPT')
    args=p.parse_args()
    try:
        if args.check_public:
            read_public(args.root)
            print('PASS: v0.49 public interview summary structure, scope and privacy gates')
        else:
            verify_local(args.root,args.verify_local)
            print('PASS: v0.49 published interview metrics agree with the LOCAL aggregate-only v0.48 report; no records exported')
    except (Refused,OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        # Never print private input values or path in diagnostics.
        if isinstance(exc,Refused):raise SystemExit(str(exc)) from None
        raise SystemExit('INTERVIEW_SUMMARY_REFUSED: Invalid or mismatched aggregate report') from None
if __name__=='__main__':main()
