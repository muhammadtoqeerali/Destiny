"""v0.41 public documentary gate and invented-only holdback regression contracts."""
import json
import math
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
from ml.research_validation_v41 import (build,public_gate,synthetic_evaluation,document,
    MANIFEST,DICTIONARY,HARMONIZATION,MODEL,OUTPUT)

ROOT=Path(__file__).resolve().parents[1]
def src(name):return (ROOT/name).read_text(encoding='utf-8')

def test_source_review_reconciles_four_public_research_protocols():
    data=build(ROOT)
    assert data['schema']=='FRAILTYSCOPE_VALIDATION_REHEARSAL_V41'
    assert data['clinical_inference'] is False and data['registered_clinical_models']==0
    scientific=data['scientific_readiness']
    assert scientific['mapping_coverage']=={
        'historically_source_verified':3,'total_predictors':14,
        'not_mapped_in_v24_blueprint':11,'mapping_is_approved_for_clinical_serving':False}
    assert len(scientific['features'])==14
    assert sum(f['public_mapping_status']=='SOURCE_VERIFIED_PARTIAL_BLUEPRINT' for f in scientific['features'])==3
    assert all(f['source_timing_approved'] is False and f['runtime_mapping_approved'] is False
               for f in scientific['features'])
    assert scientific['prediction_index_approved'] is False
    assert len(scientific['outcome_plans'])==4
    assert all(p['patient_inference_permitted'] is False for p in scientific['outcome_plans'])
    assert all(not p['external_validation_and_calibration_approved'] for p in scientific['outcome_plans'])

def test_reproducible_public_holdback_has_no_clinical_evidence():
    assert json.loads(src(OUTPUT))==build(ROOT)
    f=synthetic_evaluation(ROOT)
    assert f['provenance']=='SYNTHETIC_GENERATED_ONLY'
    assert f['independent_clinical_validation'] is False and f['patient_data_used'] is False
    assert f['n_fit_invented']==960 and f['n_check_invented']==240
    assert len(f['metrics'])==3
    for m in f['metrics']:
        assert m['n']==240 and 0<m['synthetic_positives']<240
        assert 0<=m['synthetic_auc']<=1 and 0<=m['brier']<=1
        assert 0<=m['ece_5bins']<=1
        assert sum(b['n'] for b in m['calibration_bins'])==240
        assert len(m['calibration_bins'])==5
        assert m['brier_bootstrap_interval_95'][0]<=m['brier_bootstrap_interval_95'][1]
        assert all(math.isfinite(x) for x in (m['synthetic_auc'],m['brier'],m['ece_5bins']))

def test_cli_check_is_read_only_and_reproducible():
    r=subprocess.run([sys.executable,'-m','ml.research_validation_v41','--check'],
          cwd=ROOT,text=True,capture_output=True)
    assert r.returncode==0,r.stdout+r.stderr
    assert 'clinical inference blocked' in r.stdout

def test_public_mapping_mutations_fail_closed_without_private_files():
    # A copied *public* protocol fixture; no data/ or artifacts/ is read.
    with TemporaryDirectory(prefix='v41-source-contract-') as folder:
        root=Path(folder)
        sources=[MANIFEST,DICTIONARY,HARMONIZATION,MODEL,
                 'research/cases/nhanes_workflow_v29.json']
        for rel in sources:
            dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(src(rel),encoding='utf-8')
        r=public_gate(root)
        assert r['clinical_inference'] is False
        path=root/HARMONIZATION
        original=json.loads(path.read_text())
        tampered=json.loads(json.dumps(original))
        tampered['unmapped_predictors'].pop()
        path.write_text(json.dumps(tampered),encoding='utf-8')
        with pytest.raises(ValueError,match='mapping changed'):public_gate(root)
        path.write_text(json.dumps(original),encoding='utf-8')
        dictionary=root/DICTIONARY
        doc=json.loads(dictionary.read_text())
        doc['predictors']['age']['source_timing_verified_by_study_team']=True
        dictionary.write_text(json.dumps(doc),encoding='utf-8')
        with pytest.raises(ValueError,match='approval'):public_gate(root)

def test_public_endpoint_is_strictly_read_only_and_unparameterized():
    route=src('web/app/api/inference/validation/route.ts')
    for mark in ('VALIDATION_ENDPOINT_READ_ONLY','VALIDATION_ENDPOINT_NO_INPUT',
                 'VALIDATION_GATE_CLOSED','clinical_inference===false',
                 'registered_clinical_models===0',"'no-store"):
        assert mark in route
    for forbidden in ('request.json(', 'request.formData(', 'patient_id', 'SEQN',
                      'process.env.', 'predict_proba(', 'joblib.load(', 'localStorage'):
        assert forbidden not in route
    clinical=src('web/app/api/inference/route.ts')
    assert 'status:403' in clinical and 'Never accepts patient inputs' in clinical

def test_doctor_ui_source_maintains_strict_patient_isolation():
    ui=src('web/app/components/validation-gate-v41.tsx')
    workspace=src('web/app/components/clinical-workspace.tsx')
    assert '<ValidationGateV41/>' in workspace
    assert 'ValidationGateV41({profile' not in ui
    assert 'Validation rehearsal and clinical approval gate' in ui
    assert 'Patient Assessment' in ui
    for forbidden in ('fetch(', 'useEffect(', 'profile={profile}', 'localStorage', 'sessionStorage',
                      'patient_id', 'predict_proba(', 'trained_model.joblib'):
        assert forbidden not in ui
    css=src('web/app/validation-v41.css')
    assert ':focus-visible' in css and 'prefers-reduced-motion' in css
    assert "import './validation-v41.css';" in src('web/app/layout.tsx')

def test_ci_desktop_mobile_and_source_only_release_contract():
    assert 'tests/browser_validation_v41.py' in src('scripts/run_browser_qa_v34.sh')
    ci=src('.github/workflows/ci.yml')
    assert 'tests/test_validation_v41.py' in ci
    assert 'python -m ml.research_validation_v41 --check' in ci
    assert 'FRAILTYSCOPE_QA_CHROMIUM: /usr/bin/google-chrome' in ci
    qa=src('tests/browser_validation_v41.py')
    for marker in ('desktop','mobile','clinical','get(','post(','patient','no-store'):
        assert marker in qa.lower()
    script=src('scripts/publish_validation_v41.sh')
    for path in ('web/app/data/validation-readiness-v41.json','ml/research_validation_v41.py',
                 'tests/browser_validation_v41.py','tests/test_validation_v41.py'):
        assert path in script


def test_patcher_refuses_second_application_and_unknown_targets():
    from scripts.patch_validation_v41 import PATCHES, transform
    for rel, pairs in PATCHES.items():
        patched=src(rel)
        for _, new in pairs:
            assert new in patched,(rel,new)
        with pytest.raises(ValueError):
            transform(rel, patched)
    with pytest.raises(ValueError,match='Unexpected patch target'):
        transform('data/secret.csv','content')

def test_executing_from_an_unrelated_directory_does_not_require_private_data():
    # Path discovery for the public-only CLI is based on the module, not cwd.
    with TemporaryDirectory(prefix='v41-unrelated-cwd-') as folder:
        r=subprocess.run([sys.executable,str(ROOT/'ml/research_validation_v41.py'),'--check'],
           cwd=folder, env={**__import__('os').environ,'PYTHONPATH':str(ROOT)},
           capture_output=True,text=True)
        assert r.returncode==0,r.stdout+r.stderr
