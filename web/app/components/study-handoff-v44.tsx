'use client';
import {useState} from 'react';
import {ClipboardCheck,FileText,LockKeyhole,ShieldAlert} from 'lucide-react';
import dossier from '../data/study-handoff-v44.json';
type View='features'|'outcomes'|'governance';
/** Read-only public source dossier; no patient profile, network writes or clinical inference. */
export function StudyHandoffV44(){
  const [view,setView]=useState<View>('features');
  const [filter,setFilter]=useState('all');
  const fields=dossier.feature_evidence_requests.filter(f=>filter==='all'||f.source_mapping_status===filter);
  return <section className="v44-handoff" aria-label="Study team evidence handoff">
    <header><div><span className="v44-kicker"><ClipboardCheck size={17}/> STUDY TEAM HANDOFF · RESEARCH ONLY</span>
      <h3>What evidence must the study team provide?</h3>
      <p>This source-only request list explains the missing decisions before any real-model study or clinical deployment. Candidate NHANES variables are <strong>not approved patient inputs</strong>; no clinical risk is calculated.</p>
    </div><span className="v44-locked"><LockKeyhole size={16}/> Clinical promotion denied</span></header>
    <div className="v44-stat-grid"><div><b>14</b><span>predictor reviews required</span></div>
      <div><b>11</b><span>source mappings unresolved</span></div><div><b>0</b><span>prediction-time approvals</span></div>
      <div><b>4</b><span>outcome protocols pending</span></div></div>
    <div className="v44-tabs" role="group" aria-label="Study handoff categories">
      <button type="button" aria-pressed={view==='features'} onClick={()=>setView('features')}>Predictor evidence</button>
      <button type="button" aria-pressed={view==='outcomes'} onClick={()=>setView('outcomes')}>Four outcome definitions</button>
      <button type="button" aria-pressed={view==='governance'} onClick={()=>setView('governance')}>Governance &amp; validation</button>
    </div>
    {view==='features'&&<div className="v44-panel" aria-label="Predictor review requests">
      <div className="v44-filter"><label htmlFor="v44-filter">Source status</label><select id="v44-filter" value={filter} onChange={e=>setFilter(e.target.value)}>
        <option value="all">All 14 predictors</option>
        <option value="PARTIAL_2011_2012_ONLY">Three partial mappings</option>
        <option value="UNRESOLVED">Eleven unresolved mappings</option>
      </select></div>
      <div className="v44-requests">{fields.map(f=><article key={f.id}>
        <div className="v44-item-head"><strong>{f.id.replaceAll('_',' ')}</strong><span>{f.source_mapping_status==='UNRESOLVED'?'Source unresolved':'Partial 2011–2012 only'}</span></div>
        <p><b>Candidate:</b> {f.source_file_candidate} · {f.source_variables_candidate.join(', ')}</p>
        <p><b>Needed:</b> {f.deliverables[0]}; {f.deliverables[1]}</p>
        <small>Prediction timing: NOT APPROVED · Doctor-form equivalence: NOT VERIFIED</small>
      </article>)}</div>
    </div>}
    {view==='outcomes'&&<div className="v44-requests" aria-label="Outcome protocol requests">{dossier.outcome_evidence_requests.map(o=><article key={o.id}>
      <div className="v44-item-head"><strong>{o.id.replaceAll('_',' ')}</strong><span>UNAVAILABLE</span></div>
      <p><b>Reviewer:</b> {o.reviewer_role}</p><ul>{o.deliverables.map(d=><li key={d}>{d}</li>)}</ul>
    </article>)}</div>}
    {view==='governance'&&<div className="v44-requests" aria-label="Governance evidence requests">{dossier.governance_requests.map(g=><article key={g.id}>
      <div className="v44-item-head"><strong>{g.id.replaceAll('_',' ')}</strong><span>NOT RECEIVED</span></div>
      <p><b>Responsible:</b> {g.owner}</p><p>{g.required}</p>
    </article>)}</div>}
    <footer><ShieldAlert size={19}/><p><strong>No approvals are being claimed.</strong> Historical NHANES all-cause mortality is not an incident-disease model. Baseline diabetes, stroke or heart-failure histories cannot establish future diagnoses. Review and sign confidential evidence outside this public repository.</p></footer>
    <p className="v44-source"><FileText size={15}/> Public, blank CSV request template: <code>research/templates/STUDY_TEAM_EVIDENCE_REQUEST_V44.csv</code>. No evidence was submitted through this page.</p>
  </section>;
}
