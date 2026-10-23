"""FrailtyScope v0.44 public-only study-team evidence handoff.

Read-only. Does not open participant tables, patient forms, target rows,
private review files, serialized models, or infer approval from candidate metadata.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

SCHEMA='FRAILTYSCOPE_STUDY_HANDOFF_V44'
TRANSLATION='web/app/data/model-translation-v42.json'
ARTIFACT='web/app/data/artifact-acceptance-v43.json'
READINESS='web/app/data/inference-readiness-v39.json'
WORKFLOW='research/cases/nhanes_workflow_v29.json'
OUTPUT='web/app/data/study-handoff-v44.json'
CSV_OUTPUT='research/templates/STUDY_TEAM_EVIDENCE_REQUEST_V44.csv'
SOURCES=(TRANSLATION,ARTIFACT,READINESS,WORKFLOW)
FEATURES=('age','bmi','walking_difficulty','stairs_difficulty','stooping_difficulty',
 'heart_failure','coronary_disease','stroke','cancer','diabetes','hypertension',
 'ever_smoked','phq9_score','sex')
SENSITIVE_TOKENS=('patient_id','date_of_birth','participant_record','participant_id','SEQN',
 'password','private_key','raw_predictions','joblib.load','pickle.load')


def require(condition,message):
    if not condition: raise ValueError('STUDY_HANDOFF_REFUSED: '+message)


def source_bytes(root:Path,rel:str)->bytes:
    require(rel in SOURCES or rel in (OUTPUT,CSV_OUTPUT),'Non-allowlisted source')
    p=root/rel
    require(p.is_file() and not p.is_symlink(),'Missing/unsafe public file: '+rel)
    return p.read_bytes()


def doc(root:Path,rel:str)->dict:
    data=json.loads(source_bytes(root,rel))
    require(type(data) is dict,'Expected public JSON object: '+rel)
    return data


def build(root:Path)->dict:
    translation=doc(root,TRANSLATION)
    artifact=doc(root,ARTIFACT)
    readiness=doc(root,READINESS)
    workflow=doc(root,WORKFLOW)
    require(translation.get('schema')=='FRAILTYSCOPE_SOURCE_TO_FORM_PROMOTION_V42',
            'Translation schema changed')
    require(translation.get('clinical_promotion_decision')=='DENIED' and
            translation.get('clinical_inference') is False and
            translation.get('registered_clinical_models')==0,
            'Translation decision changed')
    require(translation.get('dictionary_candidate_coverage')==14 and
            translation.get('verified_harmonization_source_mappings')==3 and
            translation.get('unmapped_harmonization_features')==11 and
            translation.get('prediction_time_approvals')==0,
            'Evidence counts changed')
    require(translation.get('source_dictionary_is_not_approved_runtime_mapping') is True,
            'Candidate dictionary promoted unexpectedly')
    fields=translation.get('features')
    require(type(fields) is list and len(fields)==14,'Expected exactly 14 candidate fields')
    ids=[f.get('id') for f in fields if type(f) is dict]
    require(len(ids)==14 and set(ids)==set(FEATURES) and len(set(ids))==14,
            'Predictor inventory changed')
    partially_mapped=[]
    requests=[]
    for feature in fields:
        ident=feature['id']
        partial=feature.get('source_mapping_status')=='PARTIAL_SOURCE_VERIFIED_2011_2012'
        require(feature.get('source_mapping_status') in
                ('PARTIAL_SOURCE_VERIFIED_2011_2012','UNMAPPED_IN_V24'),
                'Unsupported source mapping status for '+ident)
        require(feature.get('prediction_time_approved') is False and
                feature.get('runtime_transform_approved') is False and
                feature.get('form_equivalence_verified') is False,
                'Unsafe feature approval claim for '+ident)
        source_file=feature.get('candidate_source_file')
        source_vars=feature.get('candidate_source_variables')
        require(type(source_file) is str and source_file.endswith('.XPT') and
                type(source_vars) is list and 1<=len(source_vars)<=9 and
                all(type(v) is str and v.isalnum() for v in source_vars),
                'Unexpected candidate source identifiers for '+ident)
        if partial:partially_mapped.append(ident)
        gaps=feature.get('review_gaps')
        require(type(gaps) is list and gaps and
                all(type(g) is str and len(g)<=450 for g in gaps),
                'Missing review rationale for '+ident)
        requests.append({
          'id':ident,
          'source_file_candidate':source_file,
          'source_variables_candidate':source_vars,
          'source_mapping_status':'PARTIAL_2011_2012_ONLY' if partial else 'UNRESOLVED',
          'prediction_time_status':'NOT_APPROVED',
          'doctor_input_equivalence':'NOT_VERIFIED',
          'reviewer_role':'Study-team data dictionary / measurement expert',
          'deliverables':['Signed source-variable codebook and source-wave mapping',
                          'Index-time availability and transformation specification',
                          'Documented missingness, structural skips and Doctor-form equivalence'],
          'existing_gaps':gaps,
          'signed_review_received':False,
        })
    require(set(partially_mapped)=={'walking_difficulty','stairs_difficulty','stooping_difficulty'},
            'Partial source mappings changed')
    require(artifact.get('schema')=='FRAILTYSCOPE_ARTIFACT_ACCEPTANCE_V43' and
            artifact.get('clinical_promotion_decision')=='DENIED' and
            artifact.get('clinical_inference') is False and
            artifact.get('artifact_binary_loaded') is False and
            artifact.get('patient_data_used') is False and
            artifact.get('registered_clinical_models')==0,
            'Artifact receipt no longer blocked')
    require(readiness.get('schema')=='FRAILTYSCOPE_INFERENCE_READINESS_V39' and
            readiness.get('clinical_inference') is False and
            readiness.get('registered_clinical_models')==0 and
            readiness.get('governance_status')=='BLOCKED_FOR_NEW_ANALYSIS',
            'Public readiness changed')
    require(workflow.get('case_id')=='nhanes_mortality_v10' and
            workflow.get('prediction_index_status')=='provisional' and
            workflow.get('holdout_history')=='previously_inspected' and
            all(workflow.get(k) is False for k in ('real_data_execution_permitted',
                   'model_fitting_permitted','clinical_use_permitted',
                   'holdout_scoring_permitted','public_export_permitted')),
            'Blocked historical case changed')
    outs=translation.get('outcome_promotion')
    expected=('five_year_all_cause_mortality','incident_diabetes','incident_stroke','incident_heart_failure')
    require(type(outs) is list and len(outs)==4 and
            {x.get('id') for x in outs}==set(expected) and
            all(x.get('clinical_prediction_available') is False for x in outs),
            'Clinical outcome claims changed')
    outcome_requests=[]
    for ident in expected:
        historic=ident=='five_year_all_cause_mortality'
        outcome_requests.append({
          'id':ident,'proposed_only':True,'individual_scoring_available':False,
          'source_evidence':'HISTORICAL_MORTALITY_CASE_NOT_APPROVED' if historic else 'NO_VERIFIED_INCIDENT_TARGET_OR_APPROVED_MODEL',
          'reviewer_role':'Clinical investigator / epidemiologist',
          'deliverables':([
             'Freeze baseline MEC prediction index and approximately 5-year all-cause mortality target',
             'Document right censoring, all-cause mortality linkage and transportability',
             'Commission a new independent, previously untouched validation protocol',
          ] if historic else [
             'Define new-onset event versus prevalent history at baseline and exact prediction horizon',
             'Verify longitudinal diagnosis/event ascertainment with dates and follow-up',
             'Specify censoring, death as competing event, and external evaluation population',
          ]),
          'evidence_received':False,
        })
    gates=[
      {'id':'ethics_and_controller','owner':'Institutional data controller / ethics board',
       'required':'Written data-use authority, intended use, population, ethics and legal/regulatory determination'},
      {'id':'prediction_index','owner':'Principal investigator / study-team lead',
       'required':'Frozen index date, endpoint horizons, measurement availability and leakage review'},
      {'id':'source_mapping','owner':'NHANES questionnaire and harmonization team',
       'required':'14 approved source-to-input mappings and preprocessor parity / missingness evidence'},
      {'id':'incident_outcomes','owner':'Clinical outcomes and linkage team',
       'required':'Disease-specific incident outcomes with dates, censoring and competing event rules'},
      {'id':'model_provenance','owner':'Research ML lead / independent reviewer',
       'required':'Reproducible approved fitted model and exact preprocessor, signed immutable provenance'},
      {'id':'external_validation','owner':'Independent validation group',
       'required':'New independent untouched cohort, calibration, subgroup uncertainty and clinical utility'},
      {'id':'clinical_security','owner':'Privacy, security and clinical governance',
       'required':'Authenticated workflow, consent basis, no public PHI, clinician oversight, monitoring and rollback'},
    ]
    return {
      'schema':SCHEMA,'scope':'PUBLIC_RESEARCH_HANDOFF_NO_APPROVALS_OR_PATIENT_DATA',
      'case_id':'nhanes_mortality_v10',
      'source_sha256':{p:hashlib.sha256(source_bytes(root,p)).hexdigest() for p in SOURCES},
      'clinical_inference':False,'registered_clinical_models':0,
      'clinical_promotion_decision':'DENIED',
      'mapping_summary':{'candidate_predictors':14,'partial_source_mappings':3,
                         'unresolved_source_mappings':11,'prediction_time_approvals':0},
      'feature_evidence_requests':requests,
      'outcome_evidence_requests':outcome_requests,
      'governance_requests':[{**g,'approval_verified':False} for g in gates],
      'approval_documents_received':0,
      'next_milestone':'Authorized study-team decisions and independent evidence, not another synthetic model fit',
      'safety_note':'Questionnaire for research oversight only. Candidate source variables are not approved clinical inputs; prevalence questions do not establish incident diabetes, stroke or heart failure. Never submit patient records or confidential review documents to this public repository.',
    }


def serialize(data:dict)->str:
    return json.dumps(data,indent=2,ensure_ascii=False)+'\n'


def csv_template(receipt:dict)->str:
    out=io.StringIO(newline='')
    writer=csv.writer(out,lineterminator='\n')
    writer.writerow(['request_id','category','candidate_source','current_evidence_status',
                     'reviewer_role','requested_evidence','approval_status','evidence_reference_to_be_supplied_offline'])
    for f in receipt['feature_evidence_requests']:
        writer.writerow([f['id'],'predictor',f['source_file_candidate']+':'+','.join(f['source_variables_candidate']),
           f['source_mapping_status'],f['reviewer_role'],' / '.join(f['deliverables']),
           'NOT_RECEIVED',''])
    for o in receipt['outcome_evidence_requests']:
        writer.writerow([o['id'],'outcome','',o['source_evidence'],o['reviewer_role'],
           ' / '.join(o['deliverables']),'NOT_RECEIVED',''])
    for g in receipt['governance_requests']:
        writer.writerow([g['id'],'governance','', 'NOT_APPROVED',g['owner'],g['required'],
           'NOT_RECEIVED',''])
    return out.getvalue()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--check',action='store_true')
    p.add_argument('--print',dest='display',action='store_true')
    p.add_argument('--write-public-bundle',action='store_true',
                   help='Release-author only: regenerate public JSON and empty evidence-request CSV')
    a=p.parse_args()
    rec=build(a.root)
    if a.write_public_bundle:
        (a.root/OUTPUT).write_text(serialize(rec),encoding='utf-8')
        (a.root/CSV_OUTPUT).write_text(csv_template(rec),encoding='utf-8')
        print('WROTE empty public handoff metadata and request template; no approval created')
    if a.check:
        require(doc(a.root,OUTPUT)==rec,'Public study handoff changed')
        require(source_bytes(a.root,CSV_OUTPUT)==csv_template(rec).encode(),
                'Empty CSV handoff template changed')
        print('PASS: v0.44 handoff/14-feature study-team evidence requests reproducible; clinical gates closed')
    if a.display:print(serialize(rec),end='')
    if not (a.check or a.display or a.write_public_bundle):p.error('Select --check, --print or --write-public-bundle')

if __name__=='__main__':main()
