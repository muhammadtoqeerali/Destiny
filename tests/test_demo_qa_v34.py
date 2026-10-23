"""No private inputs: deterministic source and public-facing status contracts."""
import json
import re
from pathlib import Path

R=Path(__file__).resolve().parents[1]
def source(name):return (R/name).read_text(encoding='utf-8')

def test_server_status_only_exposes_public_release_receipt():
    s=source('web/app/api/status/route.ts')
    for v in ('FRAILTYSCOPE_PUBLIC_RELEASE_STATUS_V34','VERCEL_GIT_COMMIT_SHA',
              'git_identity_available','BLOCKED_FOR_NEW_ANALYSIS','no-store',
              'clinical_prediction: false','dynamic ='):
        assert v in s
    for forbidden in ('ADMIN_PORTAL_PASSWORD','ADMIN_SESSION_SECRET','process.env.DATA',
                      'process.env.HUNT','SEQN','PRIVATE_KEY','NEXTAUTH_SECRET'):
        assert forbidden not in s

def test_reported_stale_test_counter_removed():
    s=source('web/app/components/engine-studio-v33.tsx')
    assert 'Regression suite at v0.32' not in s and '>708<' not in s
    assert 'Synthetic repeatability' in s
    assert '<ReleaseStatusV34/>' in s
    assert 'BLOCKED_FOR_NEW_ANALYSIS' in s

def test_release_widget_distinguishes_known_and_unknown_git_sha():
    s=source('web/app/components/release-status-v34.tsx')
    assert "fetch('/api/status',{cache:'no-store'" in s
    assert 'Not available from this deployment' in s
    assert 'Checking deployment' in s
    assert 'BLOCKED_FOR_NEW_ANALYSIS' in s
    assert 'useEffect' in s

def test_browser_suite_includes_real_interactive_and_responsive_checks():
    b=source('tests/browser_qa_v34.py')
    for token in ('390','1440','Patient assessment','Visit history','admin123',
                  'definitely-not-the-passcode','Pipeline explorer','Quality & lineage',
                  'Decision quality','0.35','benefit','svg[role=',
                  'pageerror','api/status','127.0.0.1'):
        assert token in b
    assert 'https://' not in b
    sh=source('scripts/run_browser_qa_v34.sh')
    assert '127.0.0.1' in sh and 'next start' in sh
    assert 'FRAILTYSCOPE_QA_BASE=' in sh

def test_documented_historical_data_untouched_and_private_workflow_blocked():
    old=json.loads(source('web/public/data/nhanes-decision-quality-v12.json'))
    assert old['counts']=={'validation':292,'evaluation':1257,'events':246}
    assert len(old['thresholds'])==14
    cfg=json.loads(source('research/cases/nhanes_workflow_v29.json'))
    assert cfg['real_data_execution_permitted'] is False
    assert cfg['model_fitting_permitted'] is False
    assert cfg['public_export_permitted'] is False

def test_ci_runs_chromium_and_source_regression():
    s=source('.github/workflows/ci.yml')
    for w in ('tests/test_demo_qa_v34.py','playwright==1.56.0',
              'python -m playwright install chromium','scripts/run_browser_qa_v34.sh'):
        assert w in s
