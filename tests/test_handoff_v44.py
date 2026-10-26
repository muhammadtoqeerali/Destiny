"""v0.44 public research handoff contracts: zero patient data, zero approvals."""
import csv
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import pytest
from ml.study_handoff_v44 import (build,serialize,csv_template,source_bytes,
 TRANSLATION,ARTIFACT,READINESS,WORKFLOW,OUTPUT,CSV_OUTPUT)

ROOT=Path(__file__).resolve().parents[1]
def src(p):return (ROOT/p).read_text(encoding='utf-8')

def scratch():
    return TemporaryDirectory(prefix='v44-public-contract-')

def copy_public(root):
    for rel in (TRANSLATION,ARTIFACT,READINESS,WORKFLOW):
        f=root/rel;f.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/rel,f)

def test_receipt_exactly_reproducible_and_denied():
    receipt=build(ROOT)
    assert src(OUTPUT)==serialize(receipt)
    assert src(CSV_OUTPUT)==csv_template(receipt)
    assert receipt['schema']=='FRAILTYSCOPE_STUDY_HANDOFF_V44'
    assert receipt['clinical_promotion_decision']=='DENIED'
    assert receipt['registered_clinical_models']==0
    assert receipt['clinical_inference'] is False
    assert receipt['approval_documents_received']==0
    assert receipt['mapping_summary']=={'candidate_predictors':14,
       'partial_source_mappings':3,'unresolved_source_mappings':11,'prediction_time_approvals':0}


def test_csv_is_blank_review_template_not_claimed_approval():
    rows=list(csv.DictReader(io.StringIO(src(CSV_OUTPUT))))
    assert len(rows)==25
    assert [x['category'] for x in rows].count('predictor')==14
    assert [x['category'] for x in rows].count('outcome')==4
    assert [x['category'] for x in rows].count('governance')==7
    assert all(x['approval_status']=='NOT_RECEIVED' for x in rows)
    assert all(x['evidence_reference_to_be_supplied_offline']=='' for x in rows)
    assert rows[0]['request_id']=='age'


def test_all_feature_requests_require_time_mapping_and_form_parity():
    receipt=build(ROOT)
    feats=receipt['feature_evidence_requests']
    assert len({f['id'] for f in feats})==14
    assert {f['id'] for f in feats if f['source_mapping_status']=='PARTIAL_2011_2012_ONLY'}=={
      'walking_difficulty','stairs_difficulty','stooping_difficulty'}
    assert all(f['prediction_time_status']=='NOT_APPROVED' and
               f['doctor_input_equivalence']=='NOT_VERIFIED' and
               f['signed_review_received'] is False for f in feats)
    assert all(len(f['deliverables'])==3 for f in feats)


def test_diseases_cannot_substitute_prevalence_for_incidence():
    outcomes=build(ROOT)['outcome_evidence_requests']
    assert len(outcomes)==4 and all(o['individual_scoring_available'] is False for o in outcomes)
    mortality=next(x for x in outcomes if x['id']=='five_year_all_cause_mortality')
    assert 'HISTORICAL_MORTALITY_CASE_NOT_APPROVED'==mortality['source_evidence']
    for target in ('incident_diabetes','incident_stroke','incident_heart_failure'):
        o=next(x for x in outcomes if x['id']==target)
        assert 'NO_VERIFIED_INCIDENT_TARGET_OR_APPROVED_MODEL'==o['source_evidence']
        assert any('new-onset' in x for x in o['deliverables'])


def test_any_approval_claim_and_mapping_drift_fail_closed():
    with scratch() as tmp:
        root=Path(tmp);copy_public(root)
        base=json.loads((root/TRANSLATION).read_text())
        variants=[]
        for mutation in ('clinical','prediction_time','mapping','source','form'):
            x=json.loads(json.dumps(base))
            if mutation=='clinical':x['clinical_inference']=True
            elif mutation=='prediction_time':x['prediction_time_approvals']=1
            elif mutation=='mapping':x['verified_harmonization_source_mappings']=14
            elif mutation=='source':x['features'][0]['source_mapping_status']='PARTIAL_SOURCE_VERIFIED_2011_2012'
            elif mutation=='form':x['features'][0]['form_equivalence_verified']=True
            variants.append(x)
        for x in variants:
            (root/TRANSLATION).write_text(json.dumps(x))
            with pytest.raises(ValueError,match='STUDY_HANDOFF_REFUSED'):
                build(root)
        (root/TRANSLATION).write_text(json.dumps(base))
        artifact=json.loads((root/ARTIFACT).read_text())
        artifact['clinical_promotion_decision']='APPROVED'
        (root/ARTIFACT).write_text(json.dumps(artifact))
        with pytest.raises(ValueError,match='STUDY_HANDOFF_REFUSED'):
            build(root)


def test_research_flags_and_outcome_claims_fail_closed():
    with scratch() as tmp:
        root=Path(tmp);copy_public(root)
        workflow=json.loads((root/WORKFLOW).read_text())
        workflow['real_data_execution_permitted']=True
        (root/WORKFLOW).write_text(json.dumps(workflow))
        with pytest.raises(ValueError,match='STUDY_HANDOFF_REFUSED'):
            build(root)
        shutil.copy2(ROOT/WORKFLOW,root/WORKFLOW)
        doc=json.loads((root/TRANSLATION).read_text())
        doc['outcome_promotion'][0]['clinical_prediction_available']=True
        (root/TRANSLATION).write_text(json.dumps(doc))
        with pytest.raises(ValueError,match='STUDY_HANDOFF_REFUSED'):
            build(root)


def test_paths_allowlisted_and_no_links():
    with pytest.raises(ValueError,match='Non-allowlisted'):
        source_bytes(ROOT,'data/processed/nhanes_5yr_local.csv')
    with scratch() as tmp:
        root=Path(tmp);copy_public(root)
        target=root/WORKFLOW;target.unlink();target.symlink_to(ROOT/WORKFLOW)
        with pytest.raises(ValueError,match='Missing/unsafe'):
            build(root)


def test_api_is_read_only_and_fail_closed():
    route=src('web/app/api/inference/handoff/route.ts')
    for text in ('STUDY_HANDOFF_INTEGRITY_GATE_CLOSED','STUDY_HANDOFF_IS_READ_ONLY',
        'PUBLIC_HANDOFF_NO_QUERY_PARAMETERS','clinical_inference!==false',
        'registered_clinical_models!==0','approval_documents_received!==0',
        'Cache-Control','no-store','export async function POST'):
        assert text in route
    for forbidden in ('request.json(', 'request.formData(', 'predict_proba(',
       'joblib.load(', 'SEQN','patient_id','localStorage'):
        assert forbidden not in route
    assert 'status:403' in src('web/app/api/inference/route.ts')


def test_doctor_ui_and_ci_preserve_prior_contracts():
    ui=src('web/app/components/study-handoff-v44.tsx')
    page=src('web/app/components/clinical-workspace.tsx')
    assert '<StudyHandoffV44/>' in page
    assert "import {StudyHandoffV44} from './study-handoff-v44';" in page
    assert 'Study team evidence handoff' in ui and 'Doctor-form equivalence' in ui
    for forbidden in ('fetch(', 'localStorage', 'sessionStorage','JSON.stringify(profile)',
       'method:\'POST\'', '/api/predict'):
        assert forbidden not in ui
    assert "import './study-handoff-v44.css';" in src('web/app/layout.tsx')
    css=src('web/app/study-handoff-v44.css')
    assert 'focus-visible' in css and 'prefers-reduced-motion' in css
    runner=src('scripts/run_browser_qa_v34.sh')
    assert 'tests/browser_artifact_v43.py' in runner
    assert 'tests/browser_handoff_v44.py' in runner
    ci=src('.github/workflows/ci.yml')
    assert 'tests/test_handoff_v44.py' in ci
    assert 'python -m ml.study_handoff_v44 --check' in ci
    from scripts.patch_artifact_v43 import PATCHES
    for rel,pairs in PATCHES.items():
        content=src(rel)
        for _,new in pairs:assert new in content,(rel,new)
    assert 'tests/test_serving_v40.py tests/test_validation_v41.py' in ci
    assert 'FRAILTYSCOPE_QA_CHROMIUM: /usr/bin/google-chrome' in ci


def test_public_receipt_contains_no_person_level_data_or_fake_signoff():
    payload=src(OUTPUT)
    for forbidden in ('"patient_id"','"SEQN"','"date_of_birth"','"model_weights"',
       '"sigmoid"','"clinical_inference": true','"approval_verified": true'):
        assert forbidden not in payload
    assert 'No approvals' not in payload or 'no approvals' in payload.lower()
    assert all(x['approval_verified'] is False for x in build(ROOT)['governance_requests'])
