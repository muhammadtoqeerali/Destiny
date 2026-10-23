"""v0.41 deterministic PUBLIC-contract review + synthetic-only validation rehearsal.

NEVER opens private artifacts, real NHANES/HUNT rows, trained clinical models or
participant predictions. --check verifies a committed public receipt read-only.
Synthetic holdback is from the SAME invented generator; NOT external validation.
"""
from __future__ import annotations
import argparse
import json
import math
import random
from pathlib import Path
from scripts.build_fictional_models_v38 import generated, FEATURES, sigmoid
from ml.inference_readiness_v39 import build_receipt

ROOT = Path(__file__).resolve().parents[1]
MANIFEST='research/cases/nhanes_mortality_v10.json'
DICTIONARY='research/cases/nhanes_dictionary_timing_v23.json'
HARMONIZATION='research/cases/nhanes_harmonization_v24.json'
MODEL='web/app/data/fictional-model-registry-v38.json'
OUTPUT='web/app/data/validation-readiness-v41.json'
HOLDOUT_SEED=41021

def document(root:Path, rel:str)->dict:
    p=root/rel
    if p.is_symlink() or not p.is_file(): raise ValueError('Unsafe/missing public source: '+rel)
    return json.loads(p.read_text(encoding='utf-8'))

def ensure(ok:bool,why:str)->None:
    if not ok:raise ValueError(why)

def auc(ys:list[int], ps:list[float])->float|None:
    n1=sum(ys);n0=len(ys)-n1
    if not n0 or not n1:return None
    # Mann–Whitney score with proper average ranking for tied probabilities.
    order=sorted(zip(ps,ys))
    rank_sum=0.;i=0
    while i<len(order):
        j=i+1
        while j<len(order) and order[j][0]==order[i][0]:j+=1
        avg=(i+1+j)/2
        rank_sum+=avg*sum(y for _,y in order[i:j]);i=j
    return (rank_sum-n1*(n1+1)/2)/(n0*n1)

def brier(y:list[int],p:list[float])->float:
    return sum((v-t)**2 for t,v in zip(y,p))/len(y)

def ece(y:list[int],p:list[float],k:int=5)->tuple[float,list[dict]]:
    bins=[];error=0.
    for b in range(k):
        idx=[i for i,v in enumerate(p) if min(k-1,int(v*k))==b]
        if not idx:
            bins.append({'bin':b+1,'n':0,'mean_probability':None,'observed_fraction':None})
            continue
        actual=sum(y[i] for i in idx)/len(idx)
        estimate=sum(p[i] for i in idx)/len(idx)
        error+=len(idx)/len(y)*abs(actual-estimate)
        bins.append({'bin':b+1,'n':len(idx),'mean_probability':round(estimate,6),
                     'observed_fraction':round(actual,6)})
    return error,bins

def synthetic_evaluation(root:Path)->dict:
    registry=document(root,MODEL)
    ensure(registry['schema']=='FRAILTYSCOPE_FICTIONAL_MULTI_OUTCOME_V38'
           and registry['provenance']=='SYNTHETIC_GENERATED_ONLY'
           and registry['clinical_use_permitted'] is False
           and registry['independent_clinical_validation'] is False,
           'Fictional registry lost explicit nonclinical provenance')
    training=registry['training']
    ensure(training['generated_records']==1200 and training['fit_records']==960
           and training['synthetic_check_records']==240 and training['seed']==38062026
           and training['any_real_participants'] is False,'Synthetic split contract changed')
    ensure(registry['features']==FEATURES and len(registry['models'])==3,
           'Unexpected fictional feature or model registry')
    rows=generated()
    ensure(len(rows)==1200,'Invented generator size changed')
    check=rows[960:]
    metrics=[]
    for idx,model in enumerate(registry['models']):
        ensure(model['model_type']=='synthetic_logistic_regression' and
               model['trained_on']=='generated_fictional_examples' and
               model['clinical_use_permitted'] is False and model['outcome_is_real'] is False and
               set(model['weights'])==set(FEATURES),'Unexpected synthetic model')
        probs=[]; ys=[]
        for features,labels in check:
            score=model['intercept']+sum(v*model['weights'][name] for name,v in zip(FEATURES,features))
            probs.append(sigmoid(score)); ys.append(labels[idx])
        cal,bins=ece(ys,probs)
        rng=random.Random(HOLDOUT_SEED+idx)
        boot=[]
        for _ in range(150):
            ids=[rng.randrange(len(ys)) for __ in ys]
            boot.append(sum((probs[i]-ys[i])**2 for i in ids)/len(ids))
        boot.sort()
        metrics.append({
            'id':model['id'],'name':model['title'],
            'n':len(ys),'synthetic_positives':sum(ys),
            'brier':round(brier(ys,probs),6),
            'synthetic_auc':round(auc(ys,probs),6),
            'ece_5bins':round(cal,6),
            'brier_bootstrap_interval_95':[round(boot[3],6),round(boot[146],6)],
            'calibration_bins':bins,
        })
    return {
        'provenance':'SYNTHETIC_GENERATED_ONLY',
        'holdback_kind':'SAME_GENERATOR_FIXED_240_NOT_IN_MODEL_FIT',
        'independent_clinical_validation':False,
        'patient_data_used':False,
        'n_fit_invented':960,
        'n_check_invented':240,
        'metrics':metrics,
        'limitations':['Generated labels and predictors are invented, not mortality or future diseases.',
                       'The holdback shares the synthetic generator with training; not external validation.',
                       'Bootstrap ranges describe invented check rows only; not clinical confidence intervals.'],
    }

def public_gate(root:Path)->dict:
    state=build_receipt(root)
    manifest=document(root,MANIFEST)
    dictionary=document(root,DICTIONARY)
    harm=document(root,HARMONIZATION)
    ensure(manifest.get('case_id')==dictionary.get('case_id')==harm.get('case_id')==state['case_id'],
           'Public case identity mismatch')
    expected=manifest['features']['numeric']+manifest['features']['categorical']
    ensure(len(expected)==14 and len(set(expected))==14,'Case manifest no longer has 14 unique predictors')
    ensure(dictionary.get('prediction_index',{}).get('approved_by_study_team') is False and
           dictionary.get('allow_clinical_inference') is False and
           dictionary.get('prediction_index',{}).get('definition_status')=='provisional',
           'Prediction-time dictionary unexpected change')
    ensure(set(dictionary.get('predictors',{}))==set(expected),'Feature dictionary mismatch')
    ensure(harm.get('scope')=='partial_blueprint' and harm.get('real_data_execution_permitted') is False,
           'Harmonization scope unexpectedly expanded')
    waves=harm.get('waves',{}); wave=waves.get('2011-2012',{})
    ensure(wave.get('source_verified') is True,'No approved public source wave evidence')
    mapped=wave.get('features',{})
    unresolved=harm.get('unmapped_predictors',[])
    ensure(set(mapped)=={'walking_difficulty','stairs_difficulty','stooping_difficulty'}
           and len(unresolved)==11 and set(mapped).isdisjoint(unresolved)
           and set(mapped)|set(unresolved)==set(expected),
           'Public 3/14 source mapping changed: re-review necessary')
    ensure(state['registered_clinical_models']==0 and state['clinical_inference'] is False,
           'Readiness receipt clinical gate opened')
    features=[]
    for name in expected:
        info=dictionary['predictors'][name]
        ensure(info.get('source_timing_verified_by_study_team') is False and
               info.get('availability_status')=='pending_index_review',
               'Unexpected source-timing approval for '+name)
        features.append({'feature':name,'historical_source_wave':'2011-2012',
          'public_mapping_status':'SOURCE_VERIFIED_PARTIAL_BLUEPRINT' if name in mapped else 'UNRESOLVED_IN_V24_BLUEPRINT',
          'source_timing_approved':False,'runtime_mapping_approved':False})
    ids=[o['id'] for o in state['outcomes']]
    ensure(ids==['five_year_all_cause_mortality','incident_diabetes','incident_stroke','incident_heart_failure'],
           'Unexpected outcome set')
    outcome_plans=[]
    for index,item in enumerate(state['outcomes']):
        outcome_plans.append({
            'id':item['id'],'name':item['name'],
            'target_definition_status':'HISTORICAL_MORTALITY_TARGET_REQUIRES_INDEX_REVIEW' if index==0 else 'NEW_ONSET_TARGET_NOT_DEFINED',
            'baseline_prevalence_exclusion_approved':False,
            'prediction_horizon_approved':False,
            'censoring_and_competing_risks_approved':False,
            'validated_preprocessor_registered':False,
            'fitted_clinical_artifact_registered':False,
            'external_validation_and_calibration_approved':False,
            'medical_use_and_data_access_approved':False,
            'patient_inference_permitted':False,
        })
    return {
      'case_id':state['case_id'],
      'source_manifest':MANIFEST,
      'source_dictionary':DICTIONARY,
      'source_harmonization':HARMONIZATION,
      'source_readiness':'web/app/data/inference-readiness-v39.json',
      'mapping_coverage':{'historically_source_verified':len(mapped),'total_predictors':len(expected),
                          'not_mapped_in_v24_blueprint':len(unresolved),
                          'mapping_is_approved_for_clinical_serving':False},
      'prediction_index_approved':False,
      'registered_clinical_models':0,
      'clinical_inference':False,
      'features':features,
      'outcome_plans':outcome_plans,
      'next_decisions':['Study-team/index-time approval','Complete source-to-form and preprocessor mappings',
                        'Obtain disease incidence, censoring and competing-risk protocols',
                        'Obtain permitted fitted artifacts and independent clinical validation',
                        'Approve secure identity, privacy and clinician oversight before any patient scoring'],
    }

def build(root:Path=ROOT)->dict:
    return {
        'schema':'FRAILTYSCOPE_VALIDATION_REHEARSAL_V41',
        'mode':'PUBLIC_DOCUMENTS_AND_INVENTED_RECORDS_ONLY',
        'clinical_inference':False,
        'registered_clinical_models':0,
        'scientific_readiness':public_gate(root),
        'fictional_validation':synthetic_evaluation(root),
    }

def serialized(x:dict)->str:
    return json.dumps(x,indent=2,ensure_ascii=False)+'\n'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--print',dest='show',action='store_true')
    parser.add_argument('--write-public',action='store_true',help='Build public synthetic-only report; never patient data')
    parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args()
    if sum((args.check,args.show,args.write_public))!=1: parser.error('Choose exactly one action')
    data=build(args.root)
    if args.check:
        actual=document(args.root,OUTPUT)
        ensure(actual==data,'Committed public receipt differs from deterministic source review')
        print('PASS: v0.41 14-feature documentary gate and 240 fictional holdback records reproducible; clinical inference blocked')
    if args.show: print(serialized(data),end='')
    if args.write_public:
        path=args.root/OUTPUT
        ensure(not path.is_symlink(),'Unsafe report output')
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(serialized(data),encoding='utf-8')
        print('WROTE: public synthetic-only validation report',path)

if __name__=='__main__':main()
