"""v0.40 public/synthetic runtime contracts; no person-level inference or private artifacts."""
from pathlib import Path
import json
import math
ROOT=Path(__file__).resolve().parents[1]
def src(path):return (ROOT/path).read_text(encoding='utf-8')

def test_synthetic_models_have_invented_provenance_and_closed_clinical_gate():
    registry=json.loads(src('web/app/data/fictional-model-registry-v38.json'))
    readiness=json.loads(src('web/app/data/inference-readiness-v39.json'))
    assert registry['provenance']=='SYNTHETIC_GENERATED_ONLY'
    assert registry['clinical_use_permitted'] is False
    assert registry['independent_clinical_validation'] is False
    assert readiness['clinical_inference'] is False and readiness['registered_clinical_models']==0
    assert len(registry['features'])==6 and len(registry['models'])==3
    assert all(m['clinical_use_permitted'] is False and m['outcome_is_real'] is False for m in registry['models'])


def test_fixture_only_math_matches_training_registry():
    registry=json.loads(src('web/app/data/fictional-model-registry-v38.json'))
    fixtures=[(75,26,8,0,0,0),(82,30,14,1,1,1),(68,22,3,2,0,0)]
    for a,b,p,m,h,s in fixtures:
        vals=dict(zip(registry['features'],[(a-75)/10,(b-26)/8,(p-8)/8,m/2,h,s]))
        for model in registry['models']:
            terms=[vals[f]*model['weights'][f] for f in registry['features']]
            logit=model['intercept']+sum(terms)
            probability=1/(1+math.exp(-logit))
            assert 0<probability<1 and math.isfinite(logit)
            assert abs((logit-model['intercept'])-sum(terms))<1e-10
    lib=src('web/app/lib/synthetic-serving-v40.ts')
    assert 'calculateSyntheticFixture' in lib
    assert 'fixtureAllowed' in lib and 'servingSafetyGate' in lib
    assert "registry.provenance==='SYNTHETIC_GENERATED_ONLY'" in lib
    assert 'readiness.clinical_inference===false' in lib
    for f in ('fictional_reference','fictional_variant_b','fictional_variant_c'):
        assert f in lib


def test_public_synthetic_endpoint_does_not_parse_requests_or_enable_clinical_inference():
    route=src('web/app/api/inference/synthetic/route.ts')
    assert "params.getAll('fixture').length!==1" in route
    assert "k!=='fixture'" in route
    assert 'ONLY_PREDEFINED_FICTIONAL_FIXTURES' in route
    assert 'SYNTHETIC_ENDPOINT_READ_ONLY' in route
    assert "'no-store" in route
    for forbidden in ('request.json(', 'request.formData(', 'predict_proba(', 'patient_id', 'SEQN', 'model.joblib','localStorage'):
        assert forbidden not in route
    clinical=src('web/app/api/inference/route.ts')
    assert 'status:403' in clinical and 'Never accepts patient inputs' in clinical


def test_synthetic_demo_independent_of_patient_form():
    ui=src('web/app/components/synthetic-server-v40.tsx')
    page=src('web/app/components/clinical-workspace.tsx')
    assert '<SyntheticServerV40/>' in page
    assert "import {SyntheticServerV40} from './synthetic-server-v40';" in page
    assert 'function SyntheticServerV40()' in ui
    assert 'SyntheticServerV40({profile' not in ui
    assert 'GET-only fixture contract' in ui
    assert "fetch('/api/inference/synthetic?fixture='+fixture" in ui
    for forbidden in ('localStorage','sessionStorage','method:\'POST\'','patient_id','JSON.stringify(profile)'):
        assert forbidden not in ui
    css=src('web/app/inference-serving-v40.css')
    assert 'focus-visible' in css and '@media(prefers-reduced-motion:reduce)' in css
    assert "import '../inference-serving-v40.css';" in src('web/app/archive/layout.tsx')


def test_release_includes_browser_checks_and_requires_hosted_ci():
    runner=src('scripts/run_browser_qa_v34.sh')
    assert 'tests/browser_serving_v40.py' in runner
    ci=src('.github/workflows/ci.yml')
    assert 'tests/test_serving_v40.py' in ci
    assert 'FRAILTYSCOPE_QA_CHROMIUM: /usr/bin/google-chrome' in ci
    browser=src('tests/browser_serving_v40.py')
    for term in ('desktop','mobile','post(','get(','synthetic_class_1_probability','Clinical','patient'):
        assert term.lower() in browser.lower()
    assert 'RUNNER' not in browser


def test_v40_browser_contract_preserves_clinical_block_and_accepts_only_fixed_fixture_get():
    browser=src('tests/browser_inference_v37.py')
    assert '# v0.40 legacy contract: GET-only fictional fixture allowed.' in browser
    assert "synthetic_reference=BASE+'/api/inference/synthetic?fixture=fictional_reference'" in browser
    assert "all(method=='GET' and url==synthetic_reference" in browser
    # v0.37 original source contract still expects an explicit api/predict denial.
    assert "url.endswith('/api/predict')" in browser
    assert "for method,url in requests if '/api/inference' in url" in browser
    assert "assert not any(method=='POST'" in browser
    assert "assert not any(path.endswith('/api/predict') or '/api/inference'" not in browser
    css=src('web/app/inference-serving-v40.css')
    assert 'align-items:start' not in css
    assert 'align-items:flex-start' in css
    publisher=src('scripts/publish_serving_v40.sh')
    installer=src('scripts/install_serving_v40.sh')
    assert 'tests/browser_inference_v37.py' in publisher
    assert 'tests/browser_inference_v37.py' in installer
