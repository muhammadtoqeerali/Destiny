"""Public-contract-only source-to-form translation and promotion plan.

Never imports joblib/pickle, reads participant data, opens fitted artifacts, or scores people.
--check is read-only. Promotion remains permanently blocked in this release.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from ml.research_validation_v41 import public_gate
from ml.inference_readiness_v39 import build_receipt

ROOT = Path(__file__).resolve().parents[1]
DICTIONARY = 'research/cases/nhanes_dictionary_timing_v23.json'
HARMONIZATION = 'research/cases/nhanes_harmonization_v24.json'
MANIFEST = 'research/cases/nhanes_mortality_v10.json'
V41 = 'web/app/data/validation-readiness-v41.json'
OUTPUT = 'web/app/data/model-translation-v42.json'

# The UI is a research *entry* form, not an authorized NHANES raw-code data feed.
# These are user-facing labels and observed form contracts, not approved mappings.
FORM = {
 'age': ('Age (years)', 'number, 65–110'),
 'sex': ('Sex', 'Female / Male / not recorded'),
 'bmi': ('Body mass index (kg/m²)', 'number, 10–70'),
 'walking_difficulty': ('Walking difficulty', 'descriptive response or missing status'),
 'stairs_difficulty': ('Stair difficulty', 'descriptive response or missing status'),
 'stooping_difficulty': ('Stooping difficulty', 'descriptive response or missing status'),
 'heart_failure': ('Heart failure', 'Yes / No / not recorded'),
 'coronary_disease': ('Coronary disease', 'Yes / No / not recorded'),
 'stroke': ('Stroke', 'Yes / No / not recorded'),
 'cancer': ('Cancer', 'Yes / No / not recorded'),
 'diabetes': ('Diabetes', 'Yes / No / not recorded'),
 'hypertension': ('Hypertension', 'Yes / No / not recorded'),
 'ever_smoked': ('Smoking history', 'Yes / No / not recorded'),
 'phq9_score': ('PHQ-9 total (0–27)', 'integer, 0–27'),
}

GAPS = {
 'age': ['NHANES public-use ages 80+ are top-coded; Doctor form permits 81–110. Never infer unobserved ages from RIDAGEYR.'],
 'bmi': ['Existing research source logic documents 12–70, while Doctor input currently permits 10–70.'],
 'sex': ['Survey raw codes and human-readable form choices require a reviewed, exact categorical transform.'],
 'walking_difficulty': ['NHANES PFQ uses coded 1–4 difficulty, 5 nonperformance and item-specific PFQ054 structural skips; free form status text is not an approved source transform.'],
 'stairs_difficulty': ['NHANES PFQ uses coded 1–4 difficulty, 5 nonperformance and item-specific PFQ054 structural skips; free form status text is not an approved source transform.'],
 'stooping_difficulty': ['Code 5 nonperformance must be preserved; the PFQ054 structural skip for walking/stairs does not apply to stooping.'],
 'phq9_score': ['Nine DPQ item responses must be validated at the source before a total is derived; a manually entered total is not equivalent source evidence.'],
}


def read_public(root:Path,rel:str)->dict:
    p=root/rel
    if p.is_symlink() or not p.is_file():raise ValueError('Missing or unsafe public documentary file: '+rel)
    data=json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(data,dict):raise ValueError('Public document must be an object: '+rel)
    return data


def require(ok:bool,msg:str)->None:
    if not ok:raise ValueError(msg)


def build(root:Path=ROOT)->dict:
    review=public_gate(root)
    ready=build_receipt(root)
    v41=read_public(root,V41)
    require(v41.get('schema')=='FRAILTYSCOPE_VALIDATION_REHEARSAL_V41' and v41.get('clinical_inference') is False
            and v41.get('registered_clinical_models')==0, 'v0.41 public clinical gate changed')
    require(v41.get('scientific_readiness',{}).get('mapping_coverage')==review['mapping_coverage'],
            'Historical 14-feature readiness receipt changed')
    manifest=read_public(root,MANIFEST)
    dictionary=read_public(root,DICTIONARY)
    harmon=read_public(root,HARMONIZATION)
    names=manifest['features']['numeric']+manifest['features']['categorical']
    require(len(names)==14 and set(names)==set(FORM), 'Doctor-form field contract no longer matches 14 research predictors')
    wave=harmon['waves']['2011-2012']
    partial=wave['features'];unresolved=harmon['unmapped_predictors']
    require(set(partial)=={'walking_difficulty','stairs_difficulty','stooping_difficulty'}
            and len(unresolved)==11 and set(partial).isdisjoint(unresolved)
            and set(partial)|set(unresolved)==set(names), 'Source harmonization coverage changed')
    require(ready['clinical_inference'] is False and ready['registered_clinical_models']==0,
            'Clinical use must remain disabled')
    x=[]
    for key in names:
        d=dictionary['predictors'][key]
        require(d.get('source_timing_verified_by_study_team') is False and
                d.get('availability_status')=='pending_index_review', 'Unexpected prediction-time permission: '+key)
        src=d.get('source_file');vars_=d.get('source_variables');kind=d.get('kind');units=d.get('units')
        require(isinstance(src,str) and src.endswith('.XPT') and isinstance(vars_,list)
                and vars_ and len(set(vars_))==len(vars_) and all(isinstance(v,str) and v.isupper() for v in vars_),
                'Missing candidate dictionary source variables: '+key)
        require(isinstance(kind,str) and isinstance(units,str) and units.strip(),
                'Missing feature kind/unit contract: '+key)
        if key in partial:
            mapped=partial[key]
            require(mapped.get('source_column') in vars_ and mapped.get('kind') in ('ordinal','numeric','binary','categorical'),
                    'v0.24 source-approved partial mapping mismatch: '+key)
        label,input_contract=FORM[key]
        x.append({'id':key, 'form_label':label,'current_form_input':input_contract,
                  'candidate_source_file':src,'candidate_source_variables':vars_,
                  'dictionary_kind':kind,'dictionary_units':units,
                  'source_mapping_status':'PARTIAL_SOURCE_VERIFIED_2011_2012' if key in partial else 'UNMAPPED_IN_V24',
                  'prediction_time_approved':False,'runtime_transform_approved':False,
                  'form_equivalence_verified':False,
                  'review_gaps':GAPS.get(key,[])+['Prediction-time availability and raw-code-to-form equivalence require independent review.']})
    # A complete *candidate dictionary* is not a completed verified source mapping.
    assert sum(a['source_mapping_status']=='PARTIAL_SOURCE_VERIFIED_2011_2012' for a in x)==3
    outcomes=[]
    for original in ready['outcomes']:
        outcomes.append({'id':original['id'],'name':original['name'],'current_status':original['status'],
                         'artifact_approved':False,'preprocessor_approved':False,
                         'outcome_and_index_approved':False,'independent_validation_approved':False,
                         'calibration_and_subgroups_approved':False,
                         'data_governance_and_security_approved':False,
                         'clinical_prediction_available':False})
    return {'schema':'FRAILTYSCOPE_SOURCE_TO_FORM_PROMOTION_V42',
       'scope':'PUBLIC_SOURCE_DOCUMENTS_ONLY_NO_PATIENT_OR_MODEL_DATA',
       'case_id':ready['case_id'],'clinical_inference':False,'registered_clinical_models':0,
       'dictionary_candidate_coverage':14,
       'verified_harmonization_source_mappings':3,'unmapped_harmonization_features':11,
       'prediction_time_approvals':0,
       'source_dictionary_is_not_approved_runtime_mapping':True,
       'clinical_promotion_decision':'DENIED',
       'sources':[MANIFEST,DICTIONARY,HARMONIZATION,V41],
       'features':x,'outcome_promotion':outcomes,
       'scientific_next_actions':[
           'Obtain ethics, controller, clinical intent and permissible source-access approvals.',
           'Freeze index, predictor lookback, missingness and target/censoring definitions for every outcome.',
           'Source-verify and independently review all 14 feature transforms for each target population and wave.',
           'Resolve age top-coding, BMI range, PHQ-9 provenance and PFQ skip/nonperformance mismatches.',
           'Register and hash-check an authorized model and its exact preprocessor in a restricted environment.',
           'Complete representative untouched external evaluation, calibration, uncertainty and subgroup analyses.',
           'Require secure consent, authentication, audit, clinician oversight, medical-device review and rollback.',
           'Validate feature attributions against the exact approved fitted model and preprocessing version.'
       ],
       'disclaimer':'Candidate source variables are documentary references only. This receipt neither scores patients nor attests a deployable model.'}


def serialize(x:dict)->str:
    return json.dumps(x,indent=2,ensure_ascii=False)+'\n'


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT)
    modes=p.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check',action='store_true')
    modes.add_argument('--print',dest='show',action='store_true')
    modes.add_argument('--write-public',action='store_true')
    args=p.parse_args()
    report=build(args.root)
    if args.check:
        assert read_public(args.root,OUTPUT)==report, 'Outdated or altered v0.42 public document; stop publishing'
        print('PASS: v0.42 candidate source crosswalk + four denied promotion decisions reproducible')
    elif args.show:print(serialize(report),end='')
    else:
        dest=args.root/OUTPUT
        require(not dest.is_symlink(),'Unsafe output target')
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(serialize(report),encoding='utf-8')
        print('WROTE v0.42 public documentary report:',dest)

if __name__=='__main__':main()
