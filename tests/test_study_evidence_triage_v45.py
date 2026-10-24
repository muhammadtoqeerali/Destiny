"""Only public source-contract data and synthetic / temporary CSV mutations."""
from __future__ import annotations

import csv
import io
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from ml.study_evidence_triage_v45 import (
    HEADER, STATUSES, TEMPLATE, TriageRefused, public_template, triage,
)

ROOT = Path(__file__).resolve().parents[1]


def data(rows):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=HEADER, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def test_public_template_is_immutable_and_blank():
    rows = public_template(ROOT)
    assert len(rows) == 25
    assert sum(r['category'] == 'predictor' for r in rows) == 14
    assert sum(r['category'] == 'outcome' for r in rows) == 4
    assert sum(r['category'] == 'governance' for r in rows) == 7
    assert all(r['approval_status'] == 'NOT_RECEIVED' for r in rows)


def test_unmodified_private_copy_returns_denied_aggregate():
    with TemporaryDirectory(prefix='v45-review-') as temp:
        file = Path(temp)/'offline.csv'
        file.write_text(data(public_template(ROOT)), encoding='utf8')
        result = triage(ROOT,file)
    assert result['schema'] == 'FRAILTYSCOPE_STUDY_EVIDENCE_TRIAGE_V45'
    assert result['requests_checked'] == 25
    assert result['status_counts']['NOT_RECEIVED'] == 25
    assert result['clinical_inference'] is False
    assert result['clinical_promotion_decision'] == 'DENIED'
    assert result['approval_documents_verified'] == 0
    assert result['evidence_contents_opened'] is False
    assert 'OFFLINE-TICKET_' not in str(result)


def test_claimed_approvals_are_never_real_approvals():
    rows = public_template(ROOT)
    for i, row in enumerate(rows):
        row['approval_status'] = 'APPROVED'
        row['evidence_reference_to_be_supplied_offline'] = f'OFFLINE-TICKET_{i:06d}'
    with TemporaryDirectory(prefix='v45-review-') as temp:
        file = Path(temp)/'offline.csv'
        file.write_text(data(rows), encoding='utf8')
        result = triage(ROOT,file)
    assert result['status_counts']['APPROVED'] == 25
    assert len(result['claimed_signoff_request_ids_unverified']) == 25
    assert result['clinical_promotion_decision'] == 'DENIED'
    assert result['approval_documents_verified'] == 0
    assert not result['real_data_execution_permitted']
    assert not result['model_fitting_permitted']
    assert not result['signatures_verified']
    assert 'TICKET' not in str(result)


def test_all_recognized_statuses_and_category_counts():
    rows = public_template(ROOT)
    for i, row in enumerate(rows):
        s = STATUSES[i % len(STATUSES)]
        row['approval_status'] = s
        if s in ('EVIDENCE_RECEIVED','APPROVED'):
            row['evidence_reference_to_be_supplied_offline'] = f'OFFLINE-REVIEW_{i:06d}'
    with TemporaryDirectory(prefix='v45-review-') as temp:
        file = Path(temp)/'response.csv'
        file.write_text(data(rows), encoding='utf8')
        result = triage(ROOT,file)
    assert sum(result['status_counts'].values()) == 25
    assert sum(x['total'] for x in result['categories'].values()) == 25
    assert result['clinical_inference'] is False


@pytest.mark.parametrize('mutation', [
    'wrong_header', 'renamed', 'reordered', 'missing', 'duplicated',
    'changed_source', 'formula', 'slash_ref', 'url_ref', 'bare_path',
    'missing_ticket', 'unreceived_with_ticket', 'invalid_status', 'extra_column',
])
def test_malformed_or_unsafe_response_fails_closed(mutation):
    rows = public_template(ROOT)
    rows[0]['approval_status'] = 'EVIDENCE_RECEIVED'
    rows[0]['evidence_reference_to_be_supplied_offline'] = 'OFFLINE-TICKET_001001'
    if mutation == 'renamed': rows[0]['request_id'] = 'another_column'
    if mutation == 'reordered': rows[0], rows[1] = rows[1], rows[0]
    if mutation == 'missing': rows.pop()
    if mutation == 'duplicated': rows.append(dict(rows[0]))
    if mutation == 'changed_source': rows[0]['requested_evidence'] += ' PLEASE SEND PHI'
    if mutation == 'formula': rows[0]['evidence_reference_to_be_supplied_offline'] = '=HYPERLINK("http://danger")'
    if mutation == 'slash_ref': rows[0]['evidence_reference_to_be_supplied_offline'] = '../../research/private-data.csv'
    if mutation == 'url_ref': rows[0]['evidence_reference_to_be_supplied_offline'] = 'https://research.example/evidence'
    if mutation == 'bare_path': rows[0]['evidence_reference_to_be_supplied_offline'] = '/home/person/evidence'
    if mutation == 'missing_ticket': rows[0]['evidence_reference_to_be_supplied_offline'] = ''
    if mutation == 'unreceived_with_ticket': rows[0]['approval_status'] = 'NOT_RECEIVED'
    if mutation == 'invalid_status': rows[0]['approval_status'] = 'CLINICAL_APPROVED'
    if mutation == 'extra_column': rows[0]['unexpected_person_id'] = 'secret'
    s = data(rows) if mutation != 'extra_column' else data([{key:value for key,value in r.items() if key in HEADER} for r in rows]) + ',secret\n'
    if mutation == 'wrong_header': s = s.replace('request_id,category,','person_name,category,',1)
    with TemporaryDirectory(prefix='v45-review-') as temp:
        file = Path(temp)/'response.csv'
        file.write_text(s, encoding='utf8')
        with pytest.raises(TriageRefused,match='TRIAGE_REFUSED'):
            triage(ROOT,file)


def test_response_inside_public_checkout_is_rejected():
    path = ROOT / TEMPLATE
    with pytest.raises(TriageRefused,match='outside'):
        triage(ROOT,path)


def test_symlink_response_is_rejected():
    with TemporaryDirectory(prefix='v45-review-') as tmp:
        path = Path(tmp)/'responses.csv'
        path.write_text(data(public_template(ROOT)))
        symlink = Path(tmp)/'alias.csv'
        symlink.symlink_to(path)
        with pytest.raises(TriageRefused,match='Symlink'):
            triage(ROOT,symlink)


def test_oversized_and_bad_encoding_fail_closed():
    with TemporaryDirectory(prefix='v45-review-') as tmp:
        file = Path(tmp)/'response.csv'
        file.write_bytes(b'A'*140_000)
        with pytest.raises(TriageRefused,match='size'):
            triage(ROOT,file)
        file.write_bytes(b'\xff\xfe\x00')
        with pytest.raises(TriageRefused,match='binary'):
            triage(ROOT,file)


def test_no_clinical_endpoint_and_no_public_response_exports():
    assert "status:403" in (ROOT/'web/app/api/inference/route.ts').read_text()
    source = (ROOT/'ml/study_evidence_triage_v45.py').read_text()
    for forbidden in ('joblib.load(', 'pickle.load(', 'read_excel(', 'requests.get(',
                      'model.predict(', 'predict_proba(', 'patient_data.json',
                      'localStorage', 'sessionStorage'):
        assert forbidden not in source
    assert 'approval_documents_verified' in source
    ci=(ROOT/'.github/workflows/ci.yml').read_text()
    assert 'tests/test_study_evidence_triage_v45.py' in ci
    assert 'python -m ml.study_evidence_triage_v45 --check-template' in ci
    assert 'tests/test_handoff_v44.py' in ci
    # Maintain all earlier source patch contracts (adjacency of historical CI steps).
    from scripts.patch_handoff_v44 import PATCHES
    for path,pairs in PATCHES.items():
        legacy=path=='web/app/layout.tsx'  # legacy CSS now lives in web/app/archive/layout.tsx
        contents=(ROOT/('web/app/archive/layout.tsx' if legacy else path)).read_text()
        for _,new in pairs:
            new=new.replace("import './","import '../") if legacy else new
            assert new in contents, path
