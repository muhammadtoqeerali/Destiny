"""v0.43 restricted/synthetic model metadata guard tests; no private artifacts."""
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
from ml.artifact_acceptance_v43 import build,serialize,CANDIDATE,REGISTRY,VALIDATION,READINESS,TRANSLATION,WORKFLOW,OUTPUT

ROOT=Path(__file__).resolve().parents[1]
def src(name):return (ROOT/name).read_text(encoding='utf8')

def test_receipt_reproducible_and_no_clinical_model():
    doc=build(ROOT)
    assert src(OUTPUT)==serialize(doc)
    assert doc['schema']=='FRAILTYSCOPE_ARTIFACT_ACCEPTANCE_V43'
    assert doc['clinical_inference'] is False
    assert doc['registered_clinical_models']==0
    assert doc['clinical_promotion_decision']=='DENIED'
    assert doc['synthetic_registry_models']==3
    assert len(doc['synthetic_input_features'])==6
    assert doc['artifact_binary_loaded'] is False
    assert doc['patient_data_used'] is False
    assert len(doc['checks'])==10
    assert len(doc['clinical_outcomes'])==4
    assert all(x['decision']=='DENIED' for x in doc['clinical_outcomes'])

def sandbox(path):
    for name in [CANDIDATE,REGISTRY,VALIDATION,READINESS,TRANSLATION,WORKFLOW]:
        dest=path/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,dest)

def changed_doc(root,mutator):
    c=json.loads((root/CANDIDATE).read_text())
    mutator(c)
    (root/CANDIDATE).write_text(json.dumps(c))

def test_candidate_manifest_refuses_spoofing_and_unapproved_changes():
    changes=[
      lambda x:x.update(clinical_use_permitted=True),
      lambda x:x.update(real_data_execution_permitted=True),
      lambda x:x.update(promotion_requested=True),
      lambda x:x.update(artifact_binary_loaded=True),
      lambda x:x.update(patient_data_used=True),
      lambda x:x.update(clinical_artifact_registered=True),
      lambda x:x.update(signed_clinical_authorizations=['claimed_signer']),
      lambda x:x.update(registry_sha256='0'*64),
      lambda x:x.update(source_registry='../../private/model.joblib'),
      lambda x:x.update(input_features=list(reversed(x['input_features']))),
      lambda x:x.update(model_ids=list(reversed(x['model_ids']))),
      lambda x:x['preprocessor'].update(version='clinical-v1'),
      lambda x:x.update(artifact_kind='PICKLE'),
      lambda x:x.update(extraneous='value'),
    ]
    for mutation in changes:
        with TemporaryDirectory(prefix='v43-acceptance-') as folder:
            root=Path(folder);sandbox(root);changed_doc(root,mutation)
            with pytest.raises(ValueError,match='ARTIFACT_ACCEPTANCE_REFUSED'):
                build(root)

def test_tampering_registry_validation_and_workflow_is_denied():
    for name,key,val in [(REGISTRY,'clinical_use_permitted',True),
                         (VALIDATION,'registered_clinical_models',1),
                         (READINESS,'clinical_inference',True),
                         (TRANSLATION,'prediction_time_approvals',14),
                         (WORKFLOW,'clinical_use_permitted',True)]:
        with TemporaryDirectory(prefix='v43-evidence-') as folder:
            root=Path(folder);sandbox(root)
            obj=json.loads((root/name).read_text());obj[key]=val
            (root/name).write_text(json.dumps(obj))
            with pytest.raises(ValueError,match='ARTIFACT_ACCEPTANCE_REFUSED'):
                build(root)

def test_symlink_or_external_source_rejected():
    with TemporaryDirectory(prefix='v43-symlink-') as folder:
        root=Path(folder);sandbox(root)
        (root/REGISTRY).unlink()
        (root/REGISTRY).symlink_to(ROOT/REGISTRY)
        with pytest.raises(ValueError):build(root)

def test_public_artifact_api_read_only():
    route=src('web/app/api/inference/artifacts/route.ts')
    for mark in ('clinical_inference!==false','registered_clinical_models!==0',
                 "clinical_promotion_decision!=='DENIED'",'CLINICAL_ARTIFACT_GATE_CLOSED',
                 'ARTIFACT_METADATA_READ_ONLY',"result({error:'CLINICAL_ARTIFACT_GATE_CLOSED'},503)",'no-store'):
        assert mark in route
    for method in ('POST','PUT','PATCH','DELETE'):
        assert 'async function '+method+'()' in route
    for forbidden in ('request.json(', 'request.formData(', 'predict_proba(', 'joblib.load(',
                      'patient_id','SEQN','localStorage','process.env.'):
        assert forbidden not in route
    assert 'status:403' in src('web/app/api/inference/route.ts')

def test_ui_is_independent_from_patient_assessment():
    view=src('web/app/components/artifact-acceptance-v43.tsx')
    doctor=src('web/app/components/clinical-workspace.tsx')
    assert 'export function ArtifactAcceptanceV43()' in view
    assert '<ArtifactAcceptanceV43/>' in doctor
    assert 'Clinical promotion denied' in view
    assert 'Acceptance checks' in view and 'Source fingerprints' in view
    assert 'Four clinical gates' in view
    for forbidden in ('fetch(', 'XMLHttpRequest','localStorage','sessionStorage',
                      'profile={profile}', 'JSON.stringify(profile)', 'model.joblib', 'request.json('):
        assert forbidden not in view
    assert "import '../artifact-v43.css';" in src('web/app/archive/layout.tsx')

def test_browser_and_hosted_ci_are_mandatory():
    ci=src('.github/workflows/ci.yml')
    runner=src('scripts/run_browser_qa_v34.sh')
    browser=src('tests/browser_artifact_v43.py')
    assert 'python -m pytest -q tests/test_artifact_v43.py' in ci
    assert 'python -m ml.artifact_acceptance_v43 --check' in ci
    assert 'tests/browser_artifact_v43.py' in runner
    for mark in ('desktop','mobile','Artifact acceptance check list','Source fingerprints',
                 'Clinical promotion denied','/api/inference/artifacts'):
        assert mark in browser
    assert 'FRAILTYSCOPE_QA_CHROMIUM' in browser
    css=src('web/app/artifact-v43.css')
    assert 'focus-visible' in css and 'prefers-reduced-motion' in css

def test_previous_publisher_contracts_untouched():
    from scripts.patch_validation_v41 import PATCHES
    ci=src('.github/workflows/ci.yml')
    assert 'tests/test_serving_v40.py tests/test_validation_v41.py\n' in ci
    for path,replacements in PATCHES.items():
        legacy=path=='web/app/layout.tsx'  # legacy CSS now lives in web/app/archive/layout.tsx
        for _,expected in replacements:
            expected=expected.replace("import './","import '../") if legacy else expected
            assert expected in src('web/app/archive/layout.tsx' if legacy else path),(path,expected)
    assert '      - name: Verify v0.41 public research and invented holdback receipt\n        run: PYTHONPATH=. python -m ml.research_validation_v41 --check\n      - name: Public payload validation\n' in ci
    assert 'run: python -m pytest -q tests/test_translation_v42.py' in ci

def test_public_receipt_contains_only_synthetic_metadata():
    txt=src(OUTPUT)
    for value in ('SEQN','patient_id','predict_proba','model_weights','private_key','joblib','pickle'):
        assert value not in txt
    assert 'PUBLIC_SOURCE_ONLY_SYNTHETIC_ARTIFACT_METADATA' in txt
