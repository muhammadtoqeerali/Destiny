"""v0.42 public source-only translation checks; never load research participants or model binaries."""
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
from ml.model_translation_v42 import build,serialize,FORM,DICTIONARY,HARMONIZATION,MANIFEST,V41,OUTPUT

ROOT=Path(__file__).resolve().parents[1]
def src(name):return (ROOT/name).read_text(encoding='utf-8')


def test_crosswalk_reproducible_and_deny_by_default():
    report=build(ROOT)
    assert src(OUTPUT)==serialize(report)
    assert report['clinical_inference'] is False
    assert report['registered_clinical_models']==0
    assert report['clinical_promotion_decision']=='DENIED'
    assert report['dictionary_candidate_coverage']==14
    assert report['verified_harmonization_source_mappings']==3
    assert report['unmapped_harmonization_features']==11
    assert report['prediction_time_approvals']==0
    assert all(o['clinical_prediction_available'] is False for o in report['outcome_promotion'])
    assert len(report['outcome_promotion'])==4


def test_all_features_are_documentary_candidates_not_real_runtime_inputs():
    r=build(ROOT)
    assert len(r['features'])==len(FORM)==14
    assert {f['id'] for f in r['features']}==set(FORM)
    assert len([f for f in r['features'] if f['source_mapping_status']=='UNMAPPED_IN_V24'])==11
    assert len([f for f in r['features'] if f['source_mapping_status']=='PARTIAL_SOURCE_VERIFIED_2011_2012'])==3
    assert all(f['prediction_time_approved'] is False and f['runtime_transform_approved'] is False
               and f['form_equivalence_verified'] is False for f in r['features'])
    assert all(f['candidate_source_file'].endswith('.XPT') and f['candidate_source_variables'] for f in r['features'])


def test_public_contract_calls_out_known_differences():
    items={f['id']:f for f in build(ROOT)['features']}
    assert '80+' in ' '.join(items['age']['review_gaps'])
    assert '81–110' in ' '.join(items['age']['review_gaps'])
    assert '10–70' in ' '.join(items['bmi']['review_gaps'])
    assert '12–70' in ' '.join(items['bmi']['review_gaps'])
    assert 'PFQ054' in ' '.join(items['walking_difficulty']['review_gaps'])
    assert 'does not apply' in ' '.join(items['stooping_difficulty']['review_gaps'])
    assert len(items['phq9_score']['candidate_source_variables'])==9
    assert items['sex']['candidate_source_variables']==['RIAGENDR']


def prepare_temp(folder):
    for rel in [DICTIONARY,HARMONIZATION,MANIFEST,V41,'research/cases/nhanes_workflow_v29.json']:
        destination=folder/rel
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/rel,destination)


def test_tampered_mapping_or_index_or_receipt_fails_closed():
    with TemporaryDirectory(prefix='v42-review-') as tmp:
        folder=Path(tmp);prepare_temp(folder)
        a=json.loads((folder/HARMONIZATION).read_text())
        a['unmapped_predictors'].remove('age')
        (folder/HARMONIZATION).write_text(json.dumps(a))
        with pytest.raises(ValueError):build(folder)
        shutil.copyfile(ROOT/HARMONIZATION,folder/HARMONIZATION)
        b=json.loads((folder/DICTIONARY).read_text())
        b['predictors']['age']['source_timing_verified_by_study_team']=True
        (folder/DICTIONARY).write_text(json.dumps(b))
        with pytest.raises(ValueError):build(folder)
        shutil.copyfile(ROOT/DICTIONARY,folder/DICTIONARY)
        c=json.loads((folder/V41).read_text())
        c['registered_clinical_models']=1
        (folder/V41).write_text(json.dumps(c))
        with pytest.raises(ValueError):build(folder)


def test_input_ui_and_documentation_preserve_safety_boundary():
    ui=src('web/app/components/model-translation-v42.tsx')
    page=src('web/app/components/clinical-workspace.tsx')
    assert 'export function ModelTranslationV42()' in ui
    assert 'function ModelTranslationV42({profile' not in ui
    assert '<ModelTranslationV42/>' in page
    assert 'Patient assessment' in page
    assert 'SYNTHETIC' not in ui or 'patient prediction' in ui.lower()
    for forbidden in ('fetch(', 'XMLHttpRequest','localStorage','sessionStorage','JSON.stringify(profile)',
                      'request.json(', 'predict_proba(', 'model.joblib','process.env.', 'SEQN'):
        assert forbidden not in ui
    assert '3 partial' in ui and '11 unresolved' in ui
    assert "import '../translation-v42.css';" in src('web/app/archive/layout.tsx')


def test_public_api_never_accepts_patient_fields_or_enables_inference():
    route=src('web/app/api/inference/translation/route.ts')
    for marker in ('clinical_inference!==false', 'registered_clinical_models!==0',
                   "clinical_promotion_decision!=='DENIED'",'DOCUMENTARY_ENDPOINT_READ_ONLY',
                   'no-store','status:405','status:503'):
        assert marker in route
    for unsafe in ('request.json(', 'request.formData(', 'joblib', 'model.joblib',
                   'patient_id','SEQN','predict_proba(', 'localStorage'):
        assert unsafe not in route
    assert "status:403" in src('web/app/api/inference/route.ts')


def test_ci_and_browser_acceptance_are_mandatory():
    ci=src('.github/workflows/ci.yml')
    runner=src('scripts/run_browser_qa_v34.sh')
    browser=src('tests/browser_translation_v42.py')
    assert 'tests/test_translation_v42.py' in ci
    assert 'ml.model_translation_v42 --check' in ci
    assert 'tests/browser_translation_v42.py' in runner
    for text in ('desktop','mobile','Clinical','11 unresolved','3 partial','api/inference/translation'):
        assert text in browser
    assert 'FRAILTYSCOPE_QA_CHROMIUM' in browser
    css=src('web/app/translation-v42.css')
    assert 'focus-visible' in css and 'prefers-reduced-motion' in css


def test_no_private_data_or_unreviewed_models_in_public_crosswalk():
    source=src(OUTPUT)
    for marker in ('patient_id','SEQN','raw_predictions','individual_scores','model_weights','joblib','private_key'):
        assert marker not in source
    assert 'PUBLIC_SOURCE_DOCUMENTS_ONLY_NO_PATIENT_OR_MODEL_DATA' in source


def test_v41_source_contract_remains_intact_and_v42_runs_in_ci():
    # v0.41 checks each exact patch insertion stays present, even in future releases.
    from scripts.patch_validation_v41 import PATCHES
    for relative, replacements in PATCHES.items():
        legacy=relative=='web/app/layout.tsx'  # legacy CSS now lives in web/app/archive/layout.tsx
        current=src('web/app/archive/layout.tsx' if legacy else relative)
        for _, expected in replacements:
            expected=expected.replace("import './","import '../") if legacy else expected
            assert expected in current,(relative,expected)
    ci=src('.github/workflows/ci.yml')
    assert 'tests/test_serving_v40.py tests/test_validation_v41.py\n' in ci
    assert 'run: python -m pytest -q tests/test_translation_v42.py' in ci
    assert 'tests/test_validation_v41.py tests/test_translation_v42.py\n' not in ci


def test_v41_ci_receipt_step_is_adjacent_to_public_payload():
    ci=src('.github/workflows/ci.yml')
    expected=(
      '      - name: Verify v0.41 public research and invented holdback receipt\n'
      '        run: PYTHONPATH=. python -m ml.research_validation_v41 --check\n'
      '      - name: Public payload validation\n'
    )
    assert expected in ci
    assert '      - name: Verify v0.42 public source-to-form crosswalk\n' in ci
    assert '      - name: Validate v0.42 source-to-form regression contracts\n' in ci
