"""Synthetic / public-document-only contracts. No private NHANES or patient record handling."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import pytest
from ml.inference_readiness_v39 import build_receipt, serialize, CASE, PUBLIC

ROOT=Path(__file__).resolve().parents[1]
def source(path):return (ROOT/path).read_text(encoding='utf-8')

def test_readiness_manifest_reproducible_and_fail_closed():
    assert source(PUBLIC)==serialize(build_receipt(ROOT))
    report=build_receipt(ROOT)
    assert report['clinical_inference'] is False
    assert report['registered_clinical_models']==0
    assert report['governance_status']=='BLOCKED_FOR_NEW_ANALYSIS'
    assert len(report['blockers'])==7 and len(report['outcomes'])==4
    assert len(report['required_next_evidence'])==7
    assert report['source_mapping']['mapped_in_prior_documented_review']==3
    assert report['source_mapping']['required_in_prior_documented_review']==14
    assert all(o['patient_probability_available'] is False and o['approved_model'] is False for o in report['outcomes'])
    assert len({o['id'] for o in report['outcomes']})==4
    assert 'BLOCKED_HISTORICAL_CASE'==report['outcomes'][0]['status']
    assert all(o['status']=='NOT_TRAINED_OR_VALIDATED' for o in report['outcomes'][1:])

def test_documentary_research_flags_cannot_auto_enable_clinical_scoring():
    with TemporaryDirectory(prefix='v39-public-contract-') as folder:
        root=Path(folder)
        dest=root/CASE;dest.parent.mkdir(parents=True)
        source_case=json.loads(source(CASE))
        for field in ('clinical_use_permitted','models_saved','independent_validation','real_data_execution_permitted','public_export_permitted'):
            doc={**source_case,field:True}
            dest.write_text(json.dumps(doc),encoding='utf-8')
            with pytest.raises(ValueError,match='research review'):
                build_receipt(root)
        dest.write_text(json.dumps({**source_case,'prediction_index_status':'validated'}),encoding='utf-8')
        with pytest.raises(ValueError,match='review'):
            build_receipt(root)
        dest.write_text(json.dumps({**source_case,'holdout_history':'untouched'}),encoding='utf-8')
        with pytest.raises(ValueError,match='review'):
            build_receipt(root)

def test_public_status_api_cannot_score_or_receive_patient_data():
    route=source('web/app/api/inference/readiness/route.ts')
    assert "../../../data/inference-readiness-v39.json" in route
    assert 'clinical_inference !== false' in route
    assert 'registered_clinical_models !== 0' in route
    assert 'READINESS_ENDPOINT_IS_READ_ONLY' in route
    assert "'no-store" in route
    for forbidden in ('request.json(', 'predict_proba(', 'fetch(', 'model.joblib', 'localStorage', 'patient_id', 'SEQN'):
        assert forbidden not in route
    original=source('web/app/api/inference/route.ts')
    assert "status:403" in original and 'Never accepts patient inputs' in original

def test_browser_and_research_ui_contracts():
    component=source('web/app/components/inference-evidence-v39.tsx')
    ui=source('web/app/components/clinical-workspace.tsx')
    assert '<ReadinessEvidenceV39/>' in ui and 'ClinicalOutcomeRegistryV38' in ui
    assert 'ReadinessEvidenceV39' in component
    for forbidden in ('fetch(', 'localStorage', 'sessionStorage', '/api/inference/', 'patient_id', 'predict_proba('):
        assert forbidden not in component
    assert 'Verified model readiness evidence' in component
    assert 'FictionalMultiOutcomeLabV38' in ui
    css=source('web/app/inference-v39.css')
    assert 'focus-visible' in css and 'prefers-reduced-motion' in css
    assert "import './inference-v39.css';" in source('web/app/layout.tsx')
    runner=source('scripts/run_browser_qa_v34.sh')
    assert 'tests/browser_readiness_v39.py' in runner
    assert 'dirname "${BASH_SOURCE[0]}"' in runner
    assert 'FRAILTYSCOPE_ROOT:-/mnt/hdd16T/' not in runner
    ci=source('.github/workflows/ci.yml')
    assert 'tests/test_inference_readiness_v39.py' in ci
    assert 'python -m ml.inference_readiness_v39 --check' in ci
    assert 'FRAILTYSCOPE_QA_CHROMIUM: /usr/bin/google-chrome' in ci


def test_public_dossier_cannot_contain_participant_or_model_data():
    data=source(PUBLIC)
    for sensitive in ('SEQN','patient_id','model_weights','base64','predict_proba','individual_predictions', 'data_uri', 'secret_key'):
        assert sensitive not in data
    assert 'HISTORICAL_DOCUMENTARY_ONLY_NOT_REASSESSED' in data
