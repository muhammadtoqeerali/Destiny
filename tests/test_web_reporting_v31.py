"""v0.31 website source/published-aggregate checks; no participant tables or models."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def test_threshold_control_uses_actual_published_grid_option():
    component=read('web/app/components/decision-quality-v12.tsx')
    assert 'useState(String(closest.threshold))' in component
    assert 'useState(String(locked))' not in component
    data=json.loads(read('web/public/data/nhanes-decision-quality-v12.json'))
    locked=data['locked_threshold']
    values=[z['threshold'] for z in data['thresholds']]
    nearest=min(values,key=lambda p:abs(p-locked))
    assert nearest in values
    assert abs(nearest-locked)<1e-8


def test_published_historical_aggregate_math_is_internally_consistent():
    # Public, privacy-screened aggregate JSON only. No private audit/data.
    study=json.loads(read('web/public/data/nhanes-aggregate.json'))
    refined=json.loads(read('web/public/data/nhanes-refinement.json'))
    quality=json.loads(read('web/public/data/nhanes-decision-quality-v12.json'))
    assert study['counts']['total']==study['counts']['development']+study['counts']['test']
    assert refined['counts']['total']==refined['counts']['development']+refined['counts']['test']
    assert study['counts']['test']==refined['counts']['test']==quality['counts']['evaluation']==1257
    assert study['counts']['test_events']==refined['counts']['test_events']==quality['counts']['events']==246
    n=quality['counts']['evaluation']; events=quality['counts']['events']
    for item in (study['testAtF2'],refined['test'],quality['evaluation']):
        c=item['confusion']
        assert c['tp']+c['fn']==events
        assert c['tn']+c['fp']==n-events
        assert abs(item['recall']-c['tp']/events)<1e-4
        assert abs(item['precision']-c['tp']/(c['tp']+c['fp']))<1e-4
    assert len(quality['thresholds'])==14
    for point in quality['thresholds']:
        tp=point['recall']*events; fp=point['false_positive_rate']*(n-events)
        assert abs(point['predicted_positive']-(tp+fp))<0.01
        assert abs(point['precision']-tp/(tp+fp))<1e-4
        odds=point['threshold']/(1-point['threshold'])
        assert abs(point['net_benefit']-(tp-fp*odds)/n)<1e-4


def test_historical_model_roles_are_not_silently_collapsed():
    study=json.loads(read('web/public/data/nhanes-aggregate.json'))
    refined=json.loads(read('web/public/data/nhanes-refinement.json'))
    quality=json.loads(read('web/public/data/nhanes-decision-quality-v12.json'))
    assert study['selectedModel']=='CatBoost'
    assert refined['selectedModel']=='Histogram gradient boosting'
    assert quality['model']=='catboost'
    notice=read('web/app/components/research-boundary-notice.tsx')
    assert 'different earlier modeling experiments' in notice
    assert 'previously inspected' in notice
    assert 'BLOCKED_FOR_NEW_ANALYSIS' in notice
    assert '11 unmapped predictors' in notice
    for path in ('web/app/components/clinical-workspace.tsx','web/app/components/multi-outcome-admin.tsx'):
        assert '<ResearchBoundaryNotice/>' in read(path)


def test_no_demo_authentication_fallback():
    code=read('web/app/lib/auth.ts')
    assert 'admin123' not in code
    assert 'DEMO_ONLY_NOT_SECURE_' not in code
    assert 'password().length >= 16' in code
    assert 'secret().length >= 32' in code
    assert 'if (!configured()) return false' in code
    assert "if (!configured()) return '';" in code
    assert 'httpOnly: true' in code and 'sameSite:' in code


def test_assessment_does_not_label_skip_or_nonperformance_as_difficulty():
    code=read('web/app/components/clinical-workspace.tsx')
    assert "['Some difficulty','Much difficulty','Unable to do'].includes(profile[k])" in code
    for status in ('Does not do activity','Not asked (structural skip)','Refused',"Don't know"):
        assert status in code
    assert 'isValidAssessment(key,value)' in code
    assert 'invalidEntries.length>0' in code


def test_historical_results_not_recomputed_or_exported():
    # This patch never changes real public aggregate JSON, and CI continues
    # to validate their existing safe schemas and cell-level privacy rules.
    reporter=read('web/app/components/decision-quality-v12.tsx')
    assert "import research from '../../public/data/nhanes-decision-quality-v12.json'" in reporter
    assert '<ThresholdSensitivityChart' in reporter
    assert 'Separate historical experiments' not in reporter or 'Distinct historical experiments' in reporter
    assert 'independent evaluation.' not in read('web/app/components/evidence-workbench-v11.tsx').split('h2>Dataset to model outcome</h2>')[1].split('</div>',1)[0]
