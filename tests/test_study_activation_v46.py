"""Source-only and temporary synthetic response checks; never read real reviews."""
from __future__ import annotations
import csv
import io
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
from ml.study_activation_v46 import (
    SCHEMA, PUBLIC, NEXT_ACTION, WORKSTREAMS, make_plan,serialize,markdown,
)
from ml.study_evidence_triage_v45 import (
    HEADER, STATUSES, public_template,TriageRefused,
)
ROOT=Path(__file__).resolve().parents[1]

def formatted(rows):
    out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=HEADER,lineterminator='\n')
    w.writeheader();w.writerows(rows)
    return out.getvalue()

def test_public_plan_exactly_reproducible_and_never_promotes():
    result=make_plan(ROOT)
    assert serialize(result)==(ROOT/PUBLIC).read_text(encoding='utf8')
    assert result['schema']==SCHEMA and result['requests_total']==25
    assert result['basis']=='PUBLIC_BLANK_TEMPLATE_ONLY'
    assert result['status_counts']['NOT_RECEIVED']==25
    assert result['clinical_promotion_decision']=='DENIED'
    assert result['approval_documents_authenticated']==0
    assert result['patient_records_accessed'] is False
    assert result['signatures_verified'] is False
    assert result['real_data_execution_permitted'] is False
    assert result['clinical_inference'] is False
    assert len(result['actions'])==25
    assert [r['stage'] for r in result['actions']]==sorted(r['stage'] for r in result['actions'])
    assert all(r['separate_independent_review_required'] for r in result['actions'])
    assert all(r['reported_status']=='NOT_RECEIVED' for r in result['actions'])
    assert sum(x['requests'] for x in result['workstreams'])==25

def test_dependency_graph_and_reviewer_roles_are_public_and_unambiguous():
    plan=make_plan(ROOT)
    index={r['request_id']:r for r in plan['actions']}
    assert len(index)==25 and set(WORKSTREAMS).issubset(index)
    for row in plan['actions']:
        assert row['reviewer_role']
        for dep in row['depends_on_request_ids']:
            assert dep in index and index[dep]['stage']<=row['stage']
    assert index['model_provenance']['stage']<index['external_validation']['stage']
    assert index['external_validation']['stage']<index['clinical_security']['stage']
    assert index['ethics_and_controller']['stage']==0
    assert all(index[x]['stage']==2 for x in [
        'age','sex','bmi','walking_difficulty','stairs_difficulty','stooping_difficulty'
    ])
    assert 'patient_id' not in serialize(plan)

def test_markdown_public_owners_and_no_promotion():
    text=markdown(make_plan(ROOT))
    assert 'Stage 0: Authorization' in text
    assert 'Stage 5: Deployment governance' in text
    assert '**Clinical promotion: DENIED' in text
    assert 'model_provenance' in text and 'ethics_and_controller' in text
    assert 'OFFLINE-' not in text

@pytest.mark.parametrize('s',STATUSES)
def test_private_response_status_to_next_action_without_any_offline_ticket(s):
    rows=public_template(ROOT)
    rows[0]['approval_status']=s
    rows[0]['evidence_reference_to_be_supplied_offline']=(
       'OFFLINE-PRIVATE_000001' if s in ('EVIDENCE_RECEIVED','APPROVED') else ''
    )
    with TemporaryDirectory(prefix='frailtyscope-v46-fixture-') as d:
        csv_path=Path(d)/'response.csv'
        csv_path.write_text(formatted(rows),encoding='utf8')
        result=make_plan(ROOT,csv_path)
    assert result['basis']=='REDACTED_PRIVATE_RESPONSE_STATUS_ONLY'
    found={r['request_id']:r for r in result['actions']}['age']
    assert found['reported_status']==s
    assert found['next_action']==NEXT_ACTION[s]
    assert found['unverified_signoff_claim'] == (s=='APPROVED')
    for representation in (serialize(result),markdown(result)):
        assert 'OFFLINE-PRIVATE' not in representation
        assert 'response.csv' not in representation
        assert 'frailtyscope-v46-fixture-' not in representation
    assert result['clinical_promotion_decision']=='DENIED'
    assert not result['signatures_verified']

def test_all_approved_still_zero_verified_approvals():
    rows=public_template(ROOT)
    for i,r in enumerate(rows):
        r['approval_status']='APPROVED'
        r['evidence_reference_to_be_supplied_offline']=f'OFFLINE-PRIVATE_{i:06d}'
    with TemporaryDirectory(prefix='frailtyscope-v46-fixture-') as d:
        p=Path(d)/'responses.csv';p.write_text(formatted(rows),encoding='utf8')
        report=make_plan(ROOT,p)
    assert report['status_counts']['APPROVED']==25
    assert all(r['unverified_signoff_claim'] and r['separate_independent_review_required'] for r in report['actions'])
    assert all(r['next_action']=='VERIFY_CLAIMED_SIGNOFF_INDEPENDENTLY' for r in report['actions'])
    assert report['approval_documents_authenticated']==0
    assert report['clinical_promotion_decision']=='DENIED'
    assert 'OFFLINE-' not in serialize(report)

def test_modified_question_and_inrepo_private_response_refused():
    with pytest.raises(TriageRefused,match='outside'):
        make_plan(ROOT,ROOT/'research/templates/STUDY_TEAM_EVIDENCE_REQUEST_V44.csv')
    rows=public_template(ROOT)
    rows[2]['requested_evidence']='UNSAFE NEW EVIDENCE'
    with TemporaryDirectory(prefix='frailtyscope-v46-fixture-') as d:
        p=Path(d)/'response.csv';p.write_text(formatted(rows))
        with pytest.raises(TriageRefused,match='TRIAGE_REFUSED'):
            make_plan(ROOT,p)

def test_bad_ticket_and_symlink_refused():
    rows=public_template(ROOT)
    rows[0]['approval_status']='APPROVED'
    rows[0]['evidence_reference_to_be_supplied_offline']='https://example.com/private'
    with TemporaryDirectory(prefix='frailtyscope-v46-fixture-') as d:
        p=Path(d)/'response.csv';p.write_text(formatted(rows))
        with pytest.raises(TriageRefused,match='TRIAGE_REFUSED'):
            make_plan(ROOT,p)
        q=Path(d)/'alias.csv';q.symlink_to(p)
        with pytest.raises(TriageRefused,match='Symlink'):
            make_plan(ROOT,q)

def test_cli_public_check_and_json_and_markdown():
    base=[sys.executable,'-m','ml.study_activation_v46','--root',str(ROOT)]
    for args,expected in [(['--check-public-plan'],'PASS:'),
                          (['--template-plan'],'FRAILTYSCOPE_RESEARCH_ACTIVATION_PLAN_V46'),
                          (['--template-plan','--format','markdown'],'Clinical promotion: DENIED')]:
        r=subprocess.run(base+args,cwd=ROOT,capture_output=True,text=True,timeout=30)
        assert r.returncode==0,(r.stdout,r.stderr)
        assert expected in r.stdout

def test_ci_and_release_contracts_preserve_v45_and_original_clinical_block():
    ci=(ROOT/'.github/workflows/ci.yml').read_text()
    assert 'python -m ml.study_activation_v46 --check-public-plan' in ci
    assert 'tests/test_study_activation_v46.py' in ci
    from scripts.patch_triage_v45 import INSERT as V45_INSERT
    assert V45_INSERT in ci
    from scripts.patch_handoff_v44 import PATCHES as V44_PATCHES
    for rel,pairs in V44_PATCHES.items():
        data=(ROOT/rel).read_text()
        for _,new in pairs: assert new in data,rel
    assert 'status:403' in (ROOT/'web/app/api/inference/route.ts').read_text()
    mod=(ROOT/'ml/study_activation_v46.py').read_text()
    for forbidden in ('joblib.load(', 'pickle.load(', 'requests.get(',
                      'predict_proba(', 'model.fit(', 'patient_id', 'SEQN'):
        assert forbidden not in mod
    release=(ROOT/'scripts/publish_activation_v46.sh').read_text()
    assert 'tests/test_study_activation_v46.py' in release
    assert 'read -r -p' in release and 'YES' in release
