#!/usr/bin/env python3
"""Apply exact-source, reviewed UI wiring changes on the published v0.36 tree."""
from pathlib import Path
import sys

def replace_one(path,old,new):
    s=path.read_text(encoding='utf-8')
    n=s.count(old)
    if n!=1:raise SystemExit(f'ERROR: Expected one matching source anchor in {path}, found {n}')
    path.write_text(s.replace(old,new),encoding='utf-8')
    print('PATCHED:',path)

def main():
    if len(sys.argv)!=2:raise SystemExit('Usage: patch_inference_v37.py ROOT')
    root=Path(sys.argv[1]).resolve()
    page=root/'web/app/components/clinical-workspace.tsx'
    if "from './inference-readiness-v37'" in page.read_text(encoding='utf-8'):
        raise SystemExit('ERROR: v0.37 patch already applied; refusing a second application')
    replace_one(page,"import {DoctorJourneyV36, FollowUpSummaryV36, PredictionStoryV36} from './doctor-journey-v36';",
        "import {DoctorJourneyV36, FollowUpSummaryV36, PredictionStoryV36} from './doctor-journey-v36';\nimport {InferenceReadinessV37, FictionalScoringLabV37} from './inference-readiness-v37';")
    replace_one(page,"   <DoctorJourneyV36 profile={profile} visits={visits} onViewFollowUp={()=>setPage('Visit history')}/>",
        "   <InferenceReadinessV37 profile={profile} onExplore={()=>setPage('Model evidence')}/>\n   <DoctorJourneyV36 profile={profile} visits={visits} onViewFollowUp={()=>setPage('Visit history')}/>")
    replace_one(page,"     <PredictionStoryV36 profile={profile}/>",
        "     <PredictionStoryV36 profile={profile}/>\n     <FictionalScoringLabV37/>")
    replace_one(root/'web/app/layout.tsx',"import './doctor-journey-v36.css';",
        "import './doctor-journey-v36.css';\nimport './inference-v37.css';")
    replace_one(root/'scripts/run_browser_qa_v34.sh',
        'FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_doctor_v36.py',
        'FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_doctor_v36.py\nFRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_inference_v37.py')
    replace_one(root/'.github/workflows/ci.yml','tests/test_doctor_journey_v36.py',
        'tests/test_doctor_journey_v36.py tests/test_runtime_gate_v37.py')
    print('PASS: v0.37 synthetic-only model teaching lab and fail-closed readiness panel wired. Clinical inference remains prohibited.')
if __name__=='__main__':main()
