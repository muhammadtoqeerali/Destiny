"""Read-only, public metadata-only synthetic artifact acceptance rehearsal.

NEVER loads model binaries, private data, serialized pickle/joblib, participant rows or patient inputs.
Clinical promotion is DENIED regardless of metadata test success. Not a model loader.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

SCHEMA='FRAILTYSCOPE_ARTIFACT_ACCEPTANCE_V43'
CANDIDATE='research/cases/synthetic_artifact_candidate_v43.json'
REGISTRY='web/app/data/fictional-model-registry-v38.json'
VALIDATION='web/app/data/validation-readiness-v41.json'
READINESS='web/app/data/inference-readiness-v39.json'
TRANSLATION='web/app/data/model-translation-v42.json'
WORKFLOW='research/cases/nhanes_workflow_v29.json'
OUTPUT='web/app/data/artifact-acceptance-v43.json'
CANDIDATE_FIELDS={
 'schema','candidate_id','purpose','provenance','source_registry','registry_sha256',
 'source_validation','validation_sha256','model_ids','input_features','preprocessor',
 'training','artifact_kind','artifact_binary_loaded','patient_data_used',
 'clinical_use_permitted','real_data_execution_permitted','clinical_artifact_registered',
 'signed_clinical_authorizations','promotion_requested',
}
BLOCKED_FLAGS=('clinical_use_permitted','real_data_execution_permitted','model_fitting_permitted',
 'holdout_scoring_permitted','public_export_permitted','models_saved','independent_validation')

def demand(condition, message):
    if not condition: raise ValueError('ARTIFACT_ACCEPTANCE_REFUSED: '+message)

def public_bytes(root,rel):
    demand(type(rel) is str and rel and '\\' not in rel and '..' not in Path(rel).parts and
           not Path(rel).is_absolute() and rel.startswith(('research/cases/','web/app/data/')),
           'Untrusted source path')
    path=root/rel
    demand(path.is_file() and not path.is_symlink(),'Public source missing or symlink: '+rel)
    return path.read_bytes()

def public_obj(root,rel):
    data=json.loads(public_bytes(root,rel))
    demand(type(data) is dict,'Expected dictionary source: '+rel)
    return data

def sha(data):return hashlib.sha256(data).hexdigest()

def build(root:Path)->dict:
    root=Path(root)
    candidate=public_obj(root,CANDIDATE)
    demand(set(candidate)==CANDIDATE_FIELDS,'Unknown or missing candidate fields')
    demand(candidate['schema']=='FRAILTYSCOPE_SYNTHETIC_ARTIFACT_CANDIDATE_V43','Unrecognized candidate schema')
    demand(candidate['candidate_id']=='fictional_multioutcome_bundle_v38','Unexpected candidate')
    demand(candidate['purpose']=='SOFTWARE_ACCEPTANCE_REHEARSAL_ONLY' and
           candidate['provenance']=='GENERATED_FICTIONAL_EXAMPLES_ONLY','Untrusted model purpose / provenance')
    demand(candidate['source_registry']==REGISTRY and candidate['source_validation']==VALIDATION,
           'External artifact paths forbidden')
    demand(candidate['registry_sha256']==sha(public_bytes(root,REGISTRY)),'Synthetic registry checksum mismatch')
    demand(candidate['validation_sha256']==sha(public_bytes(root,VALIDATION)),'Validation receipt checksum mismatch')
    require_false=('artifact_binary_loaded','patient_data_used','clinical_use_permitted',
      'real_data_execution_permitted','clinical_artifact_registered','promotion_requested')
    demand(all(candidate[k] is False for k in require_false),'Clinical/real-data claim present')
    demand(candidate['signed_clinical_authorizations']==[],'Signature claims not permitted in synthetic rehearsal')
    demand(candidate['artifact_kind']=='PUBLIC_JSON_COEFFICIENTS_ONLY_NO_BINARY','Binary artifacts forbidden')
    reg=public_obj(root,REGISTRY)
    val=public_obj(root,VALIDATION)
    ready=public_obj(root,READINESS)
    trans=public_obj(root,TRANSLATION)
    flow=public_obj(root,WORKFLOW)
    demand(reg.get('schema')=='FRAILTYSCOPE_FICTIONAL_MULTI_OUTCOME_V38' and
           reg.get('provenance')=='SYNTHETIC_GENERATED_ONLY' and
           reg.get('clinical_use_permitted') is False and
           reg.get('independent_clinical_validation') is False,
           'Not the trusted fictional model registry')
    demand(len(reg['models'])==3 and all(m['outcome_is_real'] is False and
           m['clinical_use_permitted'] is False for m in reg['models']),
           'Synthetic registry contains real-outcome claims')
    demand(type(candidate['model_ids']) is list and
           candidate['model_ids']==[m['id'] for m in reg['models']] and
           len(set(candidate['model_ids']))==3,'Model inventory/order mismatch')
    demand(candidate['input_features']==reg['features'] and
           len(set(candidate['input_features']))==6,'Preprocessing feature ordering mismatch')
    prep=candidate['preprocessor']
    demand(type(prep) is dict and set(prep)=={'identity','version','feature_order_sha256','logic'},
           'Unknown preprocessing contract')
    demand(prep['identity']=='fixed_synthetic_v38_signals' and
           prep['version']==reg['version']=='synthetic-v38.0' and
           prep['feature_order_sha256']==sha((json.dumps(reg['features'],indent=2,ensure_ascii=False)+'\n').encode()),
           'Preprocessing fingerprint drift')
    demand(prep['logic']=='descriptive fictional transforms; not approved clinical preprocessing',
           'Unsupported preprocessing claim')
    train=candidate['training']
    demand(type(train) is dict and train=={
         'kind':'deterministic_fictional_only','seed':reg['training']['seed'],
         'fit_records':reg['training']['fit_records'],
         'holdback_records':reg['training']['synthetic_check_records']},
         'Synthetic fit/evaluation provenance mismatch')
    demand(reg['training']['any_real_participants'] is False,'Non-synthetic data claim')
    demand(val.get('schema')=='FRAILTYSCOPE_VALIDATION_REHEARSAL_V41' and
           val.get('clinical_inference') is False and val.get('registered_clinical_models')==0 and
           val['fictional_validation']['patient_data_used'] is False and
           val['fictional_validation']['independent_clinical_validation'] is False,
           'Validation receipt cannot support a clinical candidate')
    demand(ready.get('clinical_inference') is False and ready.get('registered_clinical_models')==0 and
           ready.get('governance_status')=='BLOCKED_FOR_NEW_ANALYSIS','Readiness contract changed')
    demand(trans.get('clinical_inference') is False and trans.get('registered_clinical_models')==0 and
           trans.get('clinical_promotion_decision')=='DENIED' and
           trans.get('prediction_time_approvals')==0 and
           trans.get('verified_harmonization_source_mappings')==3 and
           trans.get('unmapped_harmonization_features')==11 and
           len(trans.get('features',[]))==14,'Source-to-form evidence changed')
    demand(all(x.get('clinical_prediction_available') is False for x in trans['outcome_promotion']) and
           len(trans['outcome_promotion'])==4,'Outcome approval unexpectedly changed')
    demand(flow.get('case_id')=='nhanes_mortality_v10' and
           all(flow.get(k) is False for k in BLOCKED_FLAGS) and
           flow.get('prediction_index_status')=='provisional' and
           flow.get('holdout_history')=='previously_inspected',
           'Historical workflow permissions/index changed')
    checks=[
      ('model_inventory','MATCHED_FICTIONAL_REGISTRY','Three invented outcomes and six synthetic features agree with v0.38'),
      ('artifact_fingerprint','MATCHED_SOURCE_JSON','Public synthetic registry SHA256 matched; no model binary opened'),
      ('preprocessor_identity','MATCHED_SYNTHETIC_ONLY','Version and ordered synthetic signals match; no clinical transform'),
      ('provenance','SYNTHETIC_ONLY','Invented training records; no participant data'),
      ('validation_linkage','MATCHED_FICTIONAL_ONLY','v0.41 holdback receipt matches; not independent clinical validation'),
      ('dictionary_translation','NOT_APPROVED','3 partial mappings, 11 unresolved, 0 prediction-time approvals'),
      ('independent_clinical_evaluation','MISSING','Untouched representative external evaluation unavailable'),
      ('signed_approval','MISSING','No signed clinical authorization or controlled environment attestation'),
      ('restricted_artifact_loader','NOT_IMPLEMENTED','No approved clinical binary/preprocessor bundle in registry'),
      ('governed_serving','DENIED','Historical model clinical-use and real-data analysis remain blocked'),
    ]
    return {
      'schema':SCHEMA,
      'scope':'PUBLIC_SOURCE_ONLY_SYNTHETIC_ARTIFACT_METADATA',
      'candidate_id':candidate['candidate_id'],
      'model_registry_sha256':candidate['registry_sha256'],
      'validation_receipt_sha256':candidate['validation_sha256'],
      'synthetic_registry_models':3,
      'synthetic_input_features':candidate['input_features'],
      'synthetic_fit_records':train['fit_records'],
      'synthetic_holdback_records':train['holdback_records'],
      'artifact_binary_loaded':False,
      'patient_data_used':False,
      'clinical_inference':False,
      'registered_clinical_models':0,
      'clinical_promotion_decision':'DENIED',
      'synthetic_metadata_verdict':'STRUCTURALLY_CONSISTENT_FOR_SOFTWARE_TESTS_ONLY',
      'checks':[{'id':k,'status':v,'description':desc} for k,v,desc in checks],
      'clinical_outcomes':[{'id':x['id'],'name':x['name'],'decision':'DENIED',
            'missing':['approved target and prediction index','complete source mapping and exact preprocessor',
             'signed and hash-verified restricted model artifact','untouched clinical validation and calibration',
             'governance, clinician oversight and secure patient workflow']} for x in trans['outcome_promotion']],
      'future_secure_environment_requirements':[
       'Independent approval of clinical intent, data controller, ethics and jurisdictional device obligations',
       'Authenticated encrypted artifact store with cryptographic signatures and non-executable safe-load format',
       'Immutable provenance linking data version, outcome index, feature order and fitted preprocessing graph',
       'External holdout discrimination, calibration, uncertainty, subgroup analysis and clinical benefit review',
       'Confidential patient access, consent, event auditing, incident response, rollback and monitoring',
       'Signed promotion review separated from model developer, with environment-specific authorization',
      ],
      'public_evidence_sources':[CANDIDATE,REGISTRY,VALIDATION,READINESS,TRANSLATION,WORKFLOW],
      'disclaimer':'This is a synthetic metadata consistency drill. It verifies no real fitted model, no clinical performance, no signed clinical approval and no patient prediction.'
    }

def serialize(obj):return json.dumps(obj,indent=2,ensure_ascii=False)+'\n'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--check',action='store_true')
    p.add_argument('--print',dest='display',action='store_true')
    a=p.parse_args()
    doc=build(a.root)
    if a.check:
        demand(public_obj(a.root,OUTPUT)==doc,'Stored public receipt differs from safe source')
        print('PASS: v0.43 synthetic artifact fingerprints and denied clinical promotion are reproducible')
    if a.display:print(serialize(doc),end='')
    if not (a.check or a.display):p.error('Select --check or --print (read-only); never loads a model artifact')

if __name__=='__main__':main()
