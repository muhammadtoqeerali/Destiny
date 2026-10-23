#!/usr/bin/env python3
"""Apply strict source-only Doctor Portal transformation to exactly reviewed v0.34 anchors."""
import pathlib
import sys

root=pathlib.Path(sys.argv[1]).resolve() if len(sys.argv)==2 else pathlib.Path.cwd()
changes={
'web/app/components/clinical-workspace.tsx': [
 ("import { ResearchBoundaryNotice } from './research-boundary-notice';", "import { ResearchBoundaryNotice } from './research-boundary-notice';\nimport { DoctorHeroV35, CohortSnapshotV35 } from './doctor-visuals-v35';"),
 ('return <div className="v7-portal">', 'return <div className="v7-portal v35-doctor">'),
 ('<header className="v7-lead"><div><span className="nh-kicker"><Stethoscope size={17}/> CLINICAL INTELLIGENCE</span><h1>Clinical overview</h1><p>Population evidence, structured health assessments and visit-by-visit measurements.</p></div><span className="v7-lead-symbol"><HeartPulse size={44}/></span></header>',
  '<DoctorHeroV35 onNavigate={destination=>setPage(destination)}/>'),
 ('''<nav className="v7-topnav" aria-label="Doctor workspace">{PAGES.map(t=><button key={t} aria-current={page===t?'page':undefined} className={page===t?'active':''} onClick={()=>setPage(t)}>{t}</button>)}</nav>''',
  '''<nav className="v7-topnav" aria-label="Doctor workspace">{PAGES.map((t,i)=><button key={t} type="button" aria-label={t} aria-controls="v35-doctor-content" aria-current={page===t?'page':undefined} className={page===t?'active':''} onClick={()=>setPage(t)}><span className="v35-tab-number" aria-hidden="true">{String(i+1).padStart(2,'0')}</span>{t}</button>)}</nav>'''),
 ('<ResearchBoundaryNotice/>', '''<div className="v35-scope" role="note"><ShieldCheck size={19} aria-hidden="true"/><div><b>Historical research evidence · not a clinical prediction service</b><span>Published NHANES aggregates and temporary, de-identified browser examples only.</span><details><summary>Research scope and limitations</summary><ResearchBoundaryNotice/></details></div></div>'''),
 ("  {page==='Population overview'&&<>", "  <div id=\"v35-doctor-content\" className=\"v35-doctor-content\" role=\"region\" aria-label={page}>\n  {page==='Population overview'&&<>"),
 ('<div className="v7-two"><Box title="Participant age distribution"', '<CohortSnapshotV35/>\n   <div className="v7-two"><Box title="Participant age distribution"'),
 ('placeholder="Age" value={profile.age||\'\'}', 'placeholder="Age" aria-invalid={profile.age!==\'\'&&!isValidAssessment(\'age\',profile.age||\'\')} value={profile.age||\'\'}'),
 ('placeholder="e.g. 26.5" value={profile.bmi||\'\'}', 'placeholder="e.g. 26.5" aria-invalid={profile.bmi!==\'\'&&!isValidAssessment(\'bmi\',profile.bmi||\'\')} value={profile.bmi||\'\'}'),
 ('placeholder="0–27" value={profile.phq9_score||\'\'}', 'placeholder="0–27" aria-invalid={profile.phq9_score!==\'\'&&!isValidAssessment(\'phq9_score\',profile.phq9_score||\'\')} value={profile.phq9_score||\'\'}'),
 ('<div className="v7-completion-track"><i style={{width:100*recorded/total+\'%\'}}/></div>', '<div className="v7-completion-track" role="progressbar" aria-label="Valid assessment fields" aria-valuemin={0} aria-valuemax={total} aria-valuenow={recorded}><i style={{width:100*recorded/total+\'%\'}}/></div>'),
 ('  <footer className="v7-portal-foot">', '  </div>\n  <footer className="v7-portal-foot">'),
],
'web/app/layout.tsx':[("import './engine-studio-v34.css';", "import './engine-studio-v34.css';\nimport './doctor-v35.css';")],
'scripts/run_browser_qa_v34.sh':[(
 'FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_qa_v34.py',
 'FRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_qa_v34.py\nFRAILTYSCOPE_QA_BASE="http://127.0.0.1:$PORT" "$PY" tests/browser_doctor_v35.py')],
'.github/workflows/ci.yml':[(
 'tests/test_demo_qa_v34.py', 'tests/test_demo_qa_v34.py tests/test_doctor_v35.py'),
 ('python -m playwright install --with-deps chromium', 'python -m playwright install chromium')],
 'tests/test_demo_qa_v34.py':[(
  "'playwright install --with-deps chromium'",
  "'python -m playwright install chromium'"),
 ],
'tests/browser_qa_v34.py': [
 ("page.get_by_role('button',name='Health profiles').click()",
  "page.get_by_role('navigation',name='Doctor workspace').get_by_role('button',name='Health profiles',exact=True).click()"),
 ("page.get_by_role('button',name='Patient assessment').click()",
  "page.get_by_role('navigation',name='Doctor workspace').get_by_role('button',name='Patient assessment',exact=True).click()"),
 ("page.get_by_role('button',name='Visit history').click()",
  "page.get_by_role('navigation',name='Doctor workspace').get_by_role('button',name='Visit history',exact=True).click()"),
 ("page.get_by_role('button',name='Model evidence').click()",
  "page.get_by_role('navigation',name='Doctor workspace').get_by_role('button',name='Model evidence',exact=True).click()"),
 ],
}
# Stage transformations fully in memory. No partial edits if anchors are missing.
prepared={}
for relative,repls in changes.items():
    path=root/relative
    source=path.read_text(encoding='utf-8')
    for old,new in repls:
        if source.count(old)!=1:
            raise SystemExit(f'STOP: expected one exact v0.34 marker for {relative}, got {source.count(old)}: {old[:100]}')
        source=source.replace(old,new,1)
    prepared[path]=source
for path,source in prepared.items():
    path.write_text(source,encoding='utf-8')
    print('PATCHED:',path.relative_to(root))
print('PASS: v0.35 Doctor Portal source-only patch applied. No research data touched.')
