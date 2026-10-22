"""Synthetic-only v0.22 contract tests; no research data, fitting or inference."""
import copy
import json
from pathlib import Path

import pytest

from ml.case_governance_v22 import (
    CATALOG, IDS, REPORT_SCHEMA, SCHEMA, LOCAL_TYPES, safe_rel,
    check_evidence_reference, validate_protocol, generate_ledger,
    validate_ledger, verify_local_evidence, digest_json,
)


def fixture():
    return {'schema':SCHEMA, 'case_id':'synthetic_case',
            'use_class':'research_only','holdout_history':'locked_new',
            'prior_exploration':False, 'deployment_permitted':False,
            'expected_dataset_sha256':None,'expected_raw_source_sha256':None,
            'publish_private_evidence':False, 'related_readiness_v19':None,
            'controls':{name:{'state':'pending','note':'Not evidenced in synthetic study yet.',
                              'evidence':[]} for name in IDS},'local_evidence':[]}


def test_catalog_complete_unique_and_stage_known():
    assert len(CATALOG) == 33 and len(set(IDS))==len(IDS)
    assert all(stage in ('governance','data','design','model','evaluation','reporting','operations')
               and type(hard) is bool for _,stage,hard,_ in CATALOG)


def test_fully_pending_template_fails_closed():
    c=validate_protocol(fixture())
    report=generate_ledger(c,[])
    assert report['route']=='PROTOCOL_BLOCKED_PENDING_EVIDENCE'
    assert report['control_counts']['pending']==33
    assert len(report['critical_pending']) > 0
    assert report['clinical_use_permitted'] is False
    assert validate_ledger(c,report)['fits']==0


def test_documented_requires_evidence_and_note():
    c=fixture()
    c['controls']['data_integrity']={'state':'documented','note':'Evidence was reviewed.',
                                    'evidence':[]}
    with pytest.raises(ValueError,match='require source'):validate_protocol(c)
    c['controls']['data_integrity']['evidence']=['research/DATA_READINESS_GATE_V19.md']
    validate_protocol(c)


def test_not_applicable_requires_no_false_evidence():
    c=fixture();c['controls']['drift_monitoring']={
        'state':'not_applicable','note':'There is no deployed inference system.',
        'evidence':['research/DATA_READINESS_GATE_V19.md']}
    with pytest.raises(ValueError):validate_protocol(c)
    c['controls']['drift_monitoring']['evidence']=[]
    validate_protocol(c)


@pytest.mark.parametrize('path',[
 '/mnt/hdd16T/private.csv','data/processed/people.csv','artifacts/../data/people.csv',
 '../private/file.json','artifacts/x\nparticipant_id=12','web/public/data/sample.json',
 'file:///etc/passwd','http://example.com/doc','/tmp/log.json',
])
def test_bad_evidence_references_rejected(path):
    with pytest.raises(ValueError):check_evidence_reference(path)


@pytest.mark.parametrize('path',[
 'https://www.ntnu.edu/hunt/data/',
 'research/RESEARCH_METHODS_ATLAS_V22.md',
 'artifacts/cases/fake/report.json',
 'ml/case_engine_v10.py',
])
def test_approved_evidence_reference_shapes(path):
    check_evidence_reference(path)


@pytest.mark.parametrize('edit',[
 lambda c:c.update(deployment_permitted=True),
 lambda c:c.update(publish_private_evidence=True),
 lambda c:c.update(holdout_history='unseen'),
 lambda c:c.update(prior_exploration=None),
 lambda c:c.update(use_class='approved_clinical'),
 lambda c:c['controls'].pop('legal_access'),
 lambda c:c['controls'].update(unknown={'state':'pending','note':'Some new domain','evidence':[]}),
 lambda c:c['controls']['population_sampling'].update(note='x'),
 lambda c:c.update(related_readiness_v19='/outside/research/file.json'),
 lambda c:c.update(expected_dataset_sha256='not-a-sha'),
 lambda c:c.update(local_evidence=[{'type':'v20_pfq','path':'data/raw/people.csv','required':True}]),
])
def test_protocol_fails_closed_for_unsafe_updates(edit):
    c=fixture();edit(c)
    with pytest.raises(ValueError):validate_protocol(c)


def test_inspected_holdout_does_not_allow_na_label():
    c=fixture();c['holdout_history']='previously_inspected'
    c['controls']['splits_and_holdout']={
        'state':'not_applicable','note':'No split history exists, supposedly.','evidence':[]}
    with pytest.raises(ValueError):validate_protocol(c)


def test_limited_does_not_certify_and_prior_data_is_exploratory():
    c=fixture()
    for name in IDS:
        c['controls'][name]={'state':'documented','note':'Reviewed documentary assertion only.',
                             'evidence':['research/example.md']}
    c['controls']['outcome_index_horizon']['state']='limited'
    r=generate_ledger(validate_protocol(c),[])
    assert r['route']=='RESEARCH_REVIEW_REQUIRED'
    assert r['clinical_use_permitted'] is False
    assert not r['critical_pending']
    c['controls']['outcome_index_horizon']['state']='documented'
    assert generate_ledger(c,[])['route']=='DOCUMENTARY_CHECKLIST_COMPLETE_NOT_VALIDATED'
    c['use_class']='potential_clinical_future'
    assert generate_ledger(c,[])['route']=='CLINICAL_USE_NOT_AUTHORIZED'


def test_report_gate_rejects_false_privacy_or_route():
    c=fixture();r=generate_ledger(c,[])
    assert validate_ledger(c,r)['holdout_scored'] is False
    for key,value in [('clinical_use_permitted',True),('public_export',True),
                      ('private_data_read',True),('no_predictions_generated',False),
                      ('no_holdout_outcomes_analyzed',False),('route','READY'),
                      ('protocol_sha256','wrong')]:
        rr=copy.deepcopy(r);rr[key]=value
        with pytest.raises(ValueError):validate_ledger(c,rr)


def sample_local_obj(type_):
    obj={'schema':LOCAL_TYPES[type_],'case_id':'synthetic_case','public_export':False}
    if type_=='v19_readiness':
        obj.update(no_holdout_target_analysis=True,n_model_fits=0,n_model_scores=0,local_only=True)
    if type_=='v20_pfq':
        obj.update(holdout_labels_read=False,model_fits=0,participant_records_exported=False)
    if type_=='v21_semantics':
        obj.update(holdout_outcomes_accessed=False,model_overwritten=False,model_binary_exported=False)
    return obj


def test_only_aggregate_report_metadata_inspected(tmp_path):
    c=fixture();root=tmp_path
    for n,k in enumerate(LOCAL_TYPES):
        p=root/'artifacts'/'cases'/'synthetic_case'/f'{k}.json'
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(sample_local_obj(k)))
        c['local_evidence'].append({'type':k,'path':str(p.relative_to(root)),'required':True})
    validate_protocol(c)
    results=verify_local_evidence(c,root)
    assert len(results)==3 and all(x['state']=='metadata_valid' for x in results)
    c['expected_dataset_sha256']='a'*64
    with pytest.raises(ValueError,match='fingerprint'):verify_local_evidence(c,root)
    c['expected_dataset_sha256']=None
    # Fail closed if prior report ever claims holdout access.
    p=root/c['local_evidence'][1]['path'];x=json.loads(p.read_text())
    x['holdout_labels_read']=True;p.write_text(json.dumps(x))
    with pytest.raises(ValueError):verify_local_evidence(c,root)


def test_missing_required_metadata_blocks_and_optional_absent_is_reported(tmp_path):
    c=fixture();c['local_evidence']=[{'type':'v19_readiness',
                       'path':'artifacts/cases/synthetic_case/not_there.json','required':True}]
    with pytest.raises(ValueError):verify_local_evidence(validate_protocol(c),tmp_path)
    c['local_evidence'][0]['required']=False
    r=verify_local_evidence(validate_protocol(c),tmp_path)
    assert r[0]['state']=='unavailable_optional'


def test_private_evidence_escaping_and_duplicate_rejected(tmp_path):
    c=fixture();c['local_evidence']=[{'type':'v19_readiness',
                                  'path':'artifacts/cases/synthetic_case/../report.json','required':True}]
    with pytest.raises(ValueError):validate_protocol(c)
    c['local_evidence']=[{'type':'v19_readiness',
                       'path':'artifacts/cases/synthetic_case/report.json','required':True}]*2
    with pytest.raises(ValueError):validate_protocol(c)


def test_canonical_source_registry_is_pure():
    c=fixture();h=digest_json(c)
    assert h==digest_json(json.loads(json.dumps(c))) and len(h)==64
    assert not safe_rel('../data/source.csv','artifacts')
    assert not safe_rel('artifacts/../../etc/passwd','artifacts')


def test_module_import_never_has_trained_state():
    import ml.case_governance_v22 as m
    assert callable(m.generate_ledger) and callable(m.validate_protocol)
    assert not hasattr(m,'fitted_model')
