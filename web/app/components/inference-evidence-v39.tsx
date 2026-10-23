'use client';

import {useState} from 'react';
import {AlertTriangle,CheckCircle2,ChevronDown,ClipboardCheck,LockKeyhole,ShieldCheck,Stethoscope} from 'lucide-react';
import receipt from '../data/inference-readiness-v39.json';

type Outcome = (typeof receipt.outcomes)[number];
const decision=(outcome:Outcome)=>outcome.status==='BLOCKED_HISTORICAL_CASE'?'Existing research · blocked':'No verified disease model';

/** Public documentary readiness only. Does not accept or inspect patient form values. */
export function ReadinessEvidenceV39(){
  const [selected,setSelected]=useState(receipt.outcomes[0].id);
  const current=receipt.outcomes.find(x=>x.id===selected)||receipt.outcomes[0];
  return <section className="v39-evidence" aria-label="Verified model readiness evidence">
    <header className="v39-evidence-head"><div>
      <span className="v39-kicker"><ClipboardCheck size={16} aria-hidden="true"/> DOCUMENTARY RESEARCH READINESS</span>
      <h3>What is needed before real predictions?</h3>
      <p>This status is derived from the public research governance contract, not patient inputs. The four clinical outcomes below are not available for new-person predictions.</p>
    </div><span className="v39-status"><LockKeyhole size={16} aria-hidden="true"/> Clinical inference disabled</span></header>
    <div className="v39-evidence-metrics"><div><strong>0</strong><span>approved clinical models</span></div><div><strong>3 / 14</strong><span>source mappings reported in prior review</span></div><div><strong>4</strong><span>requested outcomes not yet enabled</span></div></div>
    <div className="v39-outcome-tabs" role="group" aria-label="Choose clinical outcome">
      {receipt.outcomes.map(outcome=><button key={outcome.id} type="button" className={outcome.id===selected?'active':''}
        aria-pressed={outcome.id===selected} onClick={()=>setSelected(outcome.id)}>{outcome.name}</button>)}
    </div>
    <div className="v39-outcome-detail" role="status"><div className="v39-detail-label"><Stethoscope size={20} aria-hidden="true"/><strong>{current.name}</strong><span>{decision(current)}</span></div>
      <p>{current.explanation}</p><p><LockKeyhole size={15} aria-hidden="true"/> No individual probability, disease forecast or model-specific explanation can be computed for this outcome.</p></div>
    <details className="v39-factors"><summary><AlertTriangle size={17} aria-hidden="true"/> Seven documented blockers <ChevronDown size={16} aria-hidden="true"/></summary>
      <ol>{receipt.blockers.map(b=><li key={b.id}><strong>{b.id.replaceAll('_',' ').toLowerCase()}</strong><span>{b.description}</span></li>)}</ol></details>
    <details className="v39-factors"><summary><ShieldCheck size={17} aria-hidden="true"/> Evidence required for the next approval stage <ChevronDown size={16} aria-hidden="true"/></summary>
      <ol>{receipt.required_next_evidence.map(s=><li key={s}><CheckCircle2 size={16} aria-hidden="true"/><span>{s}</span></li>)}</ol></details>
    <footer className="v39-evidence-foot">Source: <code>{receipt.source}</code>. The earlier 3/14 feature-mapping count is documentary and was not re-audited here. This page neither loads trained NHANES artifacts nor transmits entered assessment values.</footer>
  </section>;
}
