'use client';

import {useMemo,useState} from 'react';
import Link from 'next/link';
import {
  Activity, ArrowDownRight, ArrowRight, BarChart3, BookOpen, CheckCircle2,
  ChevronRight, CircleDot, ClipboardCheck, Database, Dna, FlaskConical,
  HeartPulse, Info, Layers3, LockKeyhole, RotateCcw, ShieldCheck, Sparkles,
  TrendingUp, Users, Waves
} from 'lucide-react';
import demo from '../data/interview-benchmark-v47.json';
import frozen from '../data/frozen-development-v66.json';

const examples=demo.fictional_examples;
const percent=(n:number,digits=1)=>`${(n*100).toFixed(digits)}%`;
const score=(n:number)=>`${(n*100).toFixed(1)}%`;
const compact=(n:number)=>n.toLocaleString('en-US');
const maxImportance=Math.max(...frozen.feature_importance.map(f=>f.delta_brier));
const positive=frozen.difficulty_n;
const negative=frozen.no_difficulty_n;
const phases=[
 {title:'Discover',meta:'Source and cohort',detail:'Public NHANES aggregates or invented teaching profiles',Icon:Database},
 {title:'Prepare',meta:'Quality and eligibility',detail:'Valid questionnaire responses and fold-safe preparation',Icon:Layers3},
 {title:'Evaluate',meta:'Model development',detail:'Compare held-out rankings and probability error',Icon:Activity},
 {title:'Communicate',meta:'Research interpretation',detail:'Understand evidence and what remains unvalidated',Icon:BarChart3}
];

type CaseFilter='all'|'none'|'some';
type EvidenceTab='overview'|'importance'|'limits';

export function DoctorFusionV66(){
 const [selected,setSelected]=useState(0);
 const [caseFilter,setCaseFilter]=useState<CaseFilter>('all');
 const [evidenceTab,setEvidenceTab]=useState<EvidenceTab>('overview');
 const current=examples[selected];
 const filtered=useMemo(()=>examples.map((p,i)=>({p,i})).filter(({p})=>caseFilter==='all'||(caseFilter==='none'?p.adl_limitations===0:p.adl_limitations>0)),[caseFilter]);
 const changeFilter=(next:CaseFilter)=>{
   setCaseFilter(next);
   const chosen=examples[selected];
   const valid=next==='all'||(next==='none'?chosen.adl_limitations===0:chosen.adl_limitations>0);
   if(!valid){const first=examples.findIndex(p=>next==='none'?p.adl_limitations===0:p.adl_limitations>0);if(first>=0)setSelected(first);}
 };
 const bars=current.illustrative_factors.slice(0,4);
 const maxMagnitude=Math.max(0.05,...bars.map(f=>Math.abs(f.log_odds_contribution)));
 return <main className="fs66" aria-label="FrailtyScope research overview">
  <section className="fs66-hero" aria-labelledby="fs66-title">
   <div className="fs66-hero-content">
    <div className="fs66-hero-eyebrow"><span className="fs66-pulse"/> DIGITAL AGEING RESEARCH <span className="fs66-hero-sep"/> EXPLORATORY DEMONSTRATOR</div>
    <h1 id="fs66-title">Making ageing<br/><span>health easier</span><br/>to understand.</h1>
    <p>One clear view of functional health examples, research evidence and machine-learning insights — without hiding the limitations.</p>
    <div className="fs66-hero-cta"><a href="#cases" className="fs66-button-primary">Explore case studio <ArrowRight size={17}/></a><a className="fs66-button-secondary" href="#evidence">See real evidence <BarChart3 size={17}/></a></div>
    <div className="fs66-hero-provenance"><ShieldCheck size={16}/> Public aggregates and fictional teaching profiles are always separate.</div>
   </div>
   <div className="fs66-hero-visual" aria-label="Frozen development benchmark preview">
    <div className="fs66-hero-visual-head"><span><span className="fs66-live-dot"/> RESEARCH SIGNAL</span><span className="fs66-hero-visual-tag">Frozen v0.64</span></div>
    <div className="fs66-benchmark-main">
      <div className="fs66-benchmark-ring" style={{background:`conic-gradient(#69e5c5 0 ${frozen.roc_auc*100}%,#233e5b ${frozen.roc_auc*100}% 100%)`}} role="img" aria-label={`Development ROC-AUC ${frozen.roc_auc.toFixed(3)}`}><span><strong>{frozen.roc_auc.toFixed(3)}</strong><small>ROC-AUC</small></span></div>
      <div className="fs66-benchmark-legend"><span>Current mobility</span><strong>Ranking performance</strong><p>Can the model rank a respondent who reports difficulty above one who does not?</p><small>2015–16 · repeated development only</small></div>
    </div>
    <div className="fs66-hero-visual-metrics"><div><span>Respondents</span><strong>{compact(frozen.cohort_n)}</strong></div><div><span>Reported difficulty</span><strong>{compact(positive)}</strong></div><div><span>Brier error</span><strong>{frozen.brier.toFixed(4)}</strong></div></div>
    <div className="fs66-hero-visual-foot"><Info size={14}/> Research metric, not clinical accuracy or a patient risk score.</div>
   </div>
   <div className="fs66-hero-orb fs66-orb-a"/><div className="fs66-hero-orb fs66-orb-b"/>
  </section>

  <section className="fs66-stat-row" aria-label="Key research numbers">
    <article className="fs66-stat-card"><div className="fs66-stat-top"><span>Study cohort</span><Users size={18}/></div><strong>{compact(frozen.cohort_n)}</strong><p>Eligible NHANES 2015–16 respondents</p><span className="fs66-stat-caption">Real public survey aggregate</span></article>
    <article className="fs66-stat-card"><div className="fs66-stat-top"><span>Reported difficulty</span><HeartPulse size={18}/></div><strong>{percent(positive/frozen.cohort_n)}</strong><p>{positive} of {frozen.cohort_n} respondents</p><div className="fs66-stat-track"><i style={{width:percent(positive/frozen.cohort_n)}}/></div></article>
    <article className="fs66-stat-card"><div className="fs66-stat-top"><span>Development ROC-AUC</span><TrendingUp size={18}/></div><strong>{frozen.roc_auc.toFixed(3)}</strong><p>Ability to rank reported walking difficulty</p><span className="fs66-stat-caption">Not classification accuracy</span></article>
    <article className="fs66-stat-card"><div className="fs66-stat-top"><span>Brier error</span><Waves size={18}/></div><strong>{frozen.brier.toFixed(4)}</strong><p>Lower means better probability accuracy</p><span className="fs66-stat-caption">Frozen logistic reference</span></article>
  </section>

  <section className="fs66-process" aria-labelledby="fs66-process-title">
   <div className="fs66-section-head"><div><span className="fs66-eyebrow">UNDER THE HOOD</span><h2 id="fs66-process-title">From data to insight.</h2><p>Four simple steps, one transparent research workflow.</p></div><span className="fs66-quiet-tag"><CircleDot size={14}/> Research workflow</span></div>
   <div className="fs66-process-grid">{phases.map(({title,meta,detail,Icon},i)=><div className="fs66-process-step" key={title}><div className="fs66-process-icon"><Icon size={22}/></div><div className="fs66-step-num">0{i+1}</div><h3>{title}</h3><strong>{meta}</strong><p>{detail}</p>{i<3&&<ChevronRight className="fs66-step-arrow" size={19} aria-hidden="true"/>}</div>)}</div>
  </section>

  <section id="cases" className="fs66-case-section" aria-labelledby="fs66-cases-title">
   <div className="fs66-section-head"><div><span className="fs66-eyebrow">INTERACTIVE TEACHING SPACE</span><h2 id="fs66-cases-title">A closer look at each profile.</h2><p>Explore eight fictional examples. These are not NHANES or HUNT participants.</p></div><span className="fs66-synthetic-tag"><FlaskConical size={15}/> GENERATED EXAMPLES</span></div>
   <div className="fs66-case-grid">
     <aside className="fs66-case-selector" aria-label="Fictional example selector"><div className="fs66-panel-head"><div><span className="fs66-eyebrow">EXAMPLE DIRECTORY</span><h3>Choose a profile</h3></div><span className="fs66-count">{filtered.length} shown</span></div>
      <div className="fs66-case-filters" aria-label="Filter profiles"><button type="button" aria-pressed={caseFilter==='all'} onClick={()=>changeFilter('all')}>All</button><button type="button" aria-pressed={caseFilter==='none'} onClick={()=>changeFilter('none')}>0 ADL</button><button type="button" aria-pressed={caseFilter==='some'} onClick={()=>changeFilter('some')}>1+ ADL</button></div>
      <div className="fs66-case-list">{filtered.map(({p,i})=><button type="button" key={p.id} className={'fs66-case-choice'+(i===selected?' is-selected':'')} aria-pressed={i===selected} onClick={()=>setSelected(i)}><span className="fs66-profile-avatar">{String(i+1).padStart(2,'0')}</span><span className="fs66-choice-main"><strong>Example {String(i+1).padStart(2,'0')}</strong><small>{p.age} years · {p.sex}</small></span><span className="fs66-choice-mini">{p.adl_limitations} ADL</span><ChevronRight size={17}/></button>)}</div>
      <div className="fs66-case-selector-foot"><Info size={15}/> All case inputs and example outcomes are invented.</div>
     </aside>
     <div className="fs66-case-detail" aria-live="polite"><div className="fs66-profile-top"><div><span className="fs66-eyebrow">FICTIONAL PROFILE · BASELINE</span><h3>Example {String(selected+1).padStart(2,'0')}</h3><p>{current.age} years · {current.sex} · Generated record</p></div><button className="fs66-reset" type="button" onClick={()=>{setSelected(0);changeFilter('all');}}><RotateCcw size={15}/> Reset</button></div>
      <div className="fs66-detail-stage">
       <div className="fs66-artificial-score"><div><span>Illustrative model score</span><small>Artificial two-year ADL outcome</small></div><div className="fs66-score-ring" style={{background:`conic-gradient(#60d6ba 0 ${current.fictional_model_probability*100}%,#29435d ${current.fictional_model_probability*100}% 100%)`}} role="img" aria-label={`Fictional model score ${score(current.fictional_model_probability)}`}><span><strong>{score(current.fictional_model_probability)}</strong><small>synthetic</small></span></div><p>This number comes from a fictional example model. It does not represent real patient prognosis.</p></div>
       <div className="fs66-clinical-metrics"><div><span>ADL limitations</span><strong>{current.adl_limitations}</strong><small>Generated baseline</small></div><div><span>Gait speed</span><strong>{current.gait_speed_mps===null?'—':`${current.gait_speed_mps} m/s`}</strong><small>Generated measurement</small></div><div><span>Grip strength</span><strong>{current.grip_strength_kg===null?'—':`${current.grip_strength_kg} kg`}</strong><small>Generated measurement</small></div></div>
      </div>
      <div className="fs66-profile-bottom"><div className="fs66-conditions"><span className="fs66-mini-label">RECORDED IN EXAMPLE</span><h4>Listed conditions</h4><div>{current.current_conditions.length?current.current_conditions.map(c=><span key={c}>{c}</span>):<span>None listed</span>}</div></div>
       <div className="fs66-explain"><div className="fs66-explain-title"><div><span className="fs66-mini-label">EXPLANATORY EXAMPLE</span><h4>Illustrative factor contributions</h4></div><span>log-odds · invented</span></div>{bars.map(f=><div key={f.feature} className="fs66-factor"><span>{f.feature.replace(/_/g,' ')}</span><div className="fs66-factor-track"><i className={f.log_odds_contribution>=0?'fs66-factor-positive':'fs66-factor-negative'} style={{width:`${Math.abs(f.log_odds_contribution)/maxMagnitude*100}%`}}/></div><strong>{f.log_odds_contribution>=0?'+':''}{f.log_odds_contribution.toFixed(2)}</strong></div>)}<p>These are source-provided artificial contributions, not SHAP explanations, treatment effects or medical recommendations.</p></div>
      </div>
     </div>
   </div>
  </section>

  <section id="evidence" className="fs66-evidence" aria-labelledby="fs66-evidence-title">
    <div className="fs66-section-head"><div><span className="fs66-eyebrow">PUBLIC DATA · REPRODUCIBLE DEVELOPMENT</span><h2 id="fs66-evidence-title">Evidence that stays honest.</h2><p>Observed survey counts and frozen development results — never mixed with fictional case scores.</p></div><span className="fs66-real-tag"><Database size={15}/> REAL NHANES AGGREGATES</span></div>
    <div className="fs66-tabbar" role="tablist" aria-label="Research evidence views"><button id="fs66-tab-overview" type="button" role="tab" aria-selected={evidenceTab==='overview'} aria-controls="fs66-evidence-content" onClick={()=>setEvidenceTab('overview')}>Cohort</button><button id="fs66-tab-importance" type="button" role="tab" aria-selected={evidenceTab==='importance'} aria-controls="fs66-evidence-content" onClick={()=>setEvidenceTab('importance')}>Feature signals</button><button id="fs66-tab-limits" type="button" role="tab" aria-selected={evidenceTab==='limits'} aria-controls="fs66-evidence-content" onClick={()=>setEvidenceTab('limits')}>Study boundaries</button></div>
    <div id="fs66-evidence-content" role="tabpanel" aria-labelledby={`fs66-tab-${evidenceTab}`} className="fs66-evidence-panel">
      {evidenceTab==='overview'&&<div className="fs66-evidence-overview"><div className="fs66-evidence-card"><div className="fs66-chart-head"><h3>Walking difficulty in the cohort</h3><span>2015–16 · unweighted</span></div><div className="fs66-cohort-stack" role="img" aria-label={`${positive} reported difficulty, ${negative} reported no difficulty`}><span style={{width:percent(positive/frozen.cohort_n)}}/><span style={{width:percent(negative/frozen.cohort_n)}}/></div><div className="fs66-cohort-legend"><div><i className="fs66-legend-positive"/><span>Reported difficulty</span><strong>{positive}</strong></div><div><i className="fs66-legend-negative"/><span>No reported difficulty</span><strong>{negative}</strong></div></div><p>Valid quarter-mile-walking responses from the eligible survey cohort. These are not nationally weighted estimates.</p></div><div className="fs66-evidence-card"><div className="fs66-chart-head"><h3>How the reference performs</h3><span>Five outer folds</span></div><div className="fs66-reference-list"><div><span>ROC-AUC <small>Higher is better</small></span><strong>{frozen.roc_auc.toFixed(3)}</strong><div><i style={{width:percent(frozen.roc_auc)}}/></div></div><div><span>PR-AUC <small>Higher is better</small></span><strong>{frozen.pr_auc.toFixed(3)}</strong><div><i style={{width:percent(frozen.pr_auc)}}/></div></div><div><span>Brier error <small>Lower is better</small></span><strong>{frozen.brier.toFixed(4)}</strong><div><i style={{width:percent(frozen.brier/frozen.dummy_brier)}}/></div></div></div><p>Development-only performance of the fixed logistic reference, not a validated clinical screening model.</p></div></div>}
      {evidenceTab==='importance'&&<div className="fs66-importance"><div className="fs66-chart-head"><h3>Which variables does the model rely on?</h3><span>Permutation ΔBrier · v0.64</span></div>{frozen.feature_importance.map(f=><div className="fs66-importance-row" key={f.feature}><strong>{f.feature}</strong><div><i style={{width:`${f.delta_brier/maxImportance*100}%`}}/></div><span>+{f.delta_brier.toFixed(4)}</span></div>)}<p>Model-dependence diagnostic on development folds. Bigger bars indicate greater sensitivity to permuting that feature, not a causal medical effect.</p></div>}
      {evidenceTab==='limits'&&<div className="fs66-limits"><div className="fs66-limits-hero"><ShieldCheck size={25}/><div><h3>Clear separation. No clinical overclaiming.</h3><p>Our design shows what is known, what is simulated, and what remains to be established.</p></div></div>{frozen.limits.map(l=><div key={l}><CheckCircle2 size={17}/><span>{l}</span></div>)}</div>}
    </div>
  </section>
  <footer className="fs66-outro"><div><span className="fs66-outro-icon"><BookOpen size={22}/></span><div><strong>Ready for the next research question.</strong><p>The detailed workspace and secure Research/Admin area remain available for the upcoming assignment.</p></div></div><div className="fs66-outro-actions"><Link href="/doctor/workspace">Detailed workspace <ArrowRight size={16}/></Link><Link href="/admin" className="fs66-outro-secondary"><LockKeyhole size={15}/> Research/Admin</Link></div></footer>
  <div className="fs66-page-note"><Dna size={14}/> FrailtyScope research demonstrator · Not a medical device, clinical decision support service or institutional deployment</div>
 </main>;
}
