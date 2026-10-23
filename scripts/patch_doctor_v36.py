#!/usr/bin/env python3
"""Strict v0.36 source-only patch. No research data and no speculative scoring."""
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve() if len(sys.argv)==2 else Path.cwd()

def one(s,old,new,file):
    n=s.count(old)
    if n!=1:
        raise SystemExit(f'STOP: {file}: expected 1 exact source anchor, got {n}: {old[:90]!r}')
    return s.replace(old,new,1)

changes={
 'web/app/components/clinical-workspace.tsx':[
  ("import { DoctorHeroV35, CohortSnapshotV35 } from './doctor-visuals-v35';",
   "import { DoctorHeroV35, CohortSnapshotV35 } from './doctor-visuals-v35';\nimport {DoctorJourneyV36, FollowUpSummaryV36, PredictionStoryV36} from './doctor-journey-v36';"),
  ('''   <Header eyebrow="STRUCTURED HEALTH PROFILE" title="Patient assessment" description="Enter measurements to organize a de-identified clinical review. Assessment details remain in this browser session and are not submitted to the server."/>''',
   '''   <Header eyebrow="STRUCTURED HEALTH PROFILE" title="Patient assessment" description="Enter de-identified observations to create a live descriptive health snapshot. No personal prediction is calculated or stored."/>\n   <DoctorJourneyV36 profile={profile} visits={visits} onViewFollowUp={()=>setPage('Visit history')}/>'''),
  ('''   <Header eyebrow="LONGITUDINAL MEASUREMENTS" title="Follow-up measurements" description="Enter dated measurements and review changes across visits. Only measurements you enter are displayed."/>''',
   '''   <Header eyebrow="LONGITUDINAL MEASUREMENTS" title="Follow-up measurements" description="Reuse assessment measurements, add dated observations, and see actual changes in this browser session. No records are fetched from a database."/>\n   <FollowUpSummaryV36 visits={visits}/>'''),
  ('''</div><button className="v7-primary" disabled={!visitDate||(!visitBmi&&!visitPhq)} onClick={addVisit}><Plus size={17}/> Add visit</button>''',
   '''</div><button type="button" className="v36-prefill" disabled={!(isValidAssessment('bmi',profile.bmi||'')||isValidAssessment('phq9_score',profile.phq9_score||''))} onClick={()=>{setVisitBmi(isValidAssessment('bmi',profile.bmi||'')?profile.bmi:'');setVisitPhq(isValidAssessment('phq9_score',profile.phq9_score||'')?profile.phq9_score:'');}}>Use assessment measurements</button><button className="v7-primary" disabled={!visitDate||(!visitBmi&&!visitPhq)} onClick={addVisit}><Plus size={17}/> Add visit</button>'''),
 ],
 'web/app/layout.tsx':[
  ("import './doctor-v35.css';","import './doctor-v35.css';\nimport './doctor-journey-v36.css';"),
 ],
 'tests/browser_doctor_v35.py':[
  ("name='Understand the model evidence'","name='How an assessment becomes an explanation'"),
 ],
 'tests/browser_qa_v34.py':[
  ("name='Understand the model evidence'","name='How an assessment becomes an explanation'"),
 ],
 'scripts/run_browser_qa_v34.sh':[
  ('FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_doctor_v35.py',
   'FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_doctor_v35.py\nFRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_doctor_v36.py'),
 ],
 '.github/workflows/ci.yml':[
  ('tests/test_doctor_v35.py','tests/test_doctor_v35.py tests/test_doctor_journey_v36.py'),
 ],
}

prepared={}
for rel,repls in changes.items():
    f=root/rel
    content=f.read_text(encoding='utf-8')
    for old,new in repls:
        content=one(content,old,new,rel)
    if rel=='web/app/components/clinical-workspace.tsx':
        start='  {page===\'Model evidence\'&&<>\n'
        end='  </>}\n  </div>\n  <footer className="v7-portal-foot">'
        if content.count(start)!=1 or content.count(end)!=1:
            raise SystemExit('STOP: model evidence section anchors differ; do not edit')
        i=content.index(start);j=content.index(end,i)
        content=content[:i]+'''   {page==='Model evidence'&&<>
     <Header eyebrow="HOW THE ENGINE WOULD WORK" title="How an assessment becomes an explanation" description="A visual walkthrough for nontechnical readers. It illustrates the process; it does not run NHANES inference or attribute real model effects."/>
     <PredictionStoryV36 profile={profile}/>
'''+content[j:]
    prepared[f]=content
for f,s in prepared.items():
    f.write_text(s,encoding='utf-8')
    print('PATCHED:',f.relative_to(root))
print('PASS: v0.36 descriptive journey and educational animation patched. Inference is still disabled.')
