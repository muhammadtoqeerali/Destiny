'use client';

import {useState} from 'react';
import Link from 'next/link';
import {Activity, ArrowRight, BarChart3, CalendarClock, ChevronRight, ClipboardList, Database, HeartPulse, Info, Layers3, ShieldCheck, Users} from 'lucide-react';
import demo from '../data/interview-benchmark-v47.json';
import mobility from '../data/real-mobility-summary-v49.json';

const examples=demo.fictional_examples;
const percent=(x:number)=>`${(x*100).toFixed(1)}%`;
const value=(x:number|null,unit:string)=>x===null?'Not recorded':`${x} ${unit}`;
const nWithADL=examples.filter(p=>p.adl_limitations>0).length;
const nWithTwoADL=examples.filter(p=>p.adl_limitations>=2).length;
const nWithOneADL=examples.filter(p=>p.adl_limitations===1).length;
const nWithoutADL=examples.length-nWithADL;
const dev=mobility.cohorts['2015-2016'];
const later=mobility.cohorts['2017-2018'];
type ProfileFilter='all'|'none'|'any';
const scoreBounds={min:Math.min(...examples.map(p=>p.fictional_model_probability)),max:Math.max(...examples.map(p=>p.fictional_model_probability))};

/** Public aggregate survey evidence and artificial case records are never joined. */
export function DoctorOverviewV51(){
 const [index,setIndex]=useState(0);
 const [filter,setFilter]=useState<ProfileFilter>('all');
 const patient=examples[index]; // All profile records and model outputs are synthetic, never real patients.
 const visible=examples.map((p,i)=>({p,i})).filter(({p})=>filter==='all'||(filter==='none'?p.adl_limitations===0:p.adl_limitations>0));
 const setSelected=(i:number,scroll=false)=>{
  setIndex(i);
  if(scroll)document.getElementById('examples')?.scrollIntoView({behavior:'auto',block:'start'});
 };
 const selectFilter=(next:ProfileFilter)=>{
  setFilter(next);
  if(next==='none'&&patient.adl_limitations>0)setIndex(examples.findIndex(p=>p.adl_limitations===0));
  if(next==='any'&&patient.adl_limitations===0)setIndex(examples.findIndex(p=>p.adl_limitations>0));
 };
 return <main className="page-wrap d51" aria-label="Doctor overview">
  <header className="d51-hero">
   <div className="d51-hero-main">
    <span className="d51-kicker"><HeartPulse size={16}/> CLINICAL OVERVIEW <i/> SYNTHETIC PROFILES</span>
    <h1>Health at a glance<span>.</span></h1>
    <p>Functional health snapshots, individual case details and population-level research.</p>
    <div className="d51-hero-links"><a href="#examples">View profiles <ArrowRight size={16}/></a><a href="#population">Population evidence <BarChart3 size={16}/></a></div>
    <span className="d51-hero-caption"><ShieldCheck size={14}/> Demonstration profiles · No real patient records or clinical alerts</span>
   </div>
   <aside className="d51-hero-aside" aria-label="Functional status distribution of fictional examples">
    <div className="d51-mix-header"><span>FUNCTIONAL STATUS MIX</span><span>{examples.length} example profiles</span></div>
    <div className="d51-mix-body">
     <div className="d51-ring" role="img" aria-label={`${nWithoutADL} examples with zero ADL limitations, ${nWithOneADL} with one and ${nWithTwoADL} with two or more`} style={{background:`conic-gradient(#53c2b0 0 ${nWithoutADL/examples.length*100}%, #e3b06a ${nWithoutADL/examples.length*100}% ${((nWithoutADL+nWithOneADL)/examples.length)*100}%, #da7a68 ${((nWithoutADL+nWithOneADL)/examples.length)*100}% 100%)`}}><span><strong>{examples.length}</strong><small>profiles</small></span></div>
     <div className="d51-mix-legend"><div><i className="d51-dot-zero"/><span>No limitations</span><strong>{nWithoutADL}</strong></div><div><i className="d51-dot-one"/><span>One limitation</span><strong>{nWithOneADL}</strong></div><div><i className="d51-dot-many"/><span>Two or more</span><strong>{nWithTwoADL}</strong></div></div>
    </div>
    <small>ADL = activities of daily living · Fictional baseline</small>
   </aside>
  </header>

  <div className="d51-section-title"><div><span className="d51-overline">SYNTHETIC DATA / OVERVIEW</span><h2>Functional snapshot</h2></div><span className="d51-source">SIMULATED DATA · NOT HUNT</span></div>
  <section className="d51-kpis" aria-label="Fictional cohort summary">
   <div className="d51-kpi"><span className="d51-kpi-icon"><Users size={19}/></span><small>Profiles in view</small><strong>{String(examples.length).padStart(2,'0')}<em> / {examples.length}</em></strong><span>Generated example records</span><div className="d51-kpi-strip d51-strip-all"><i/></div></div>
   <div className="d51-kpi"><span className="d51-kpi-icon"><Activity size={19}/></span><small>Any ADL limitation</small><strong>{String(nWithADL).padStart(2,'0')}<em> / {examples.length}</em></strong><span>{percent(nWithADL/examples.length)} of displayed examples</span><div className="d51-kpi-strip"><i style={{width:percent(nWithADL/examples.length)}}/></div></div>
   <div className="d51-kpi"><span className="d51-kpi-icon d51-icon-warm"><ClipboardList size={19}/></span><small>Two or more limitations</small><strong>{String(nWithTwoADL).padStart(2,'0')}<em> / {examples.length}</em></strong><span>{percent(nWithTwoADL/examples.length)} of displayed examples</span><div className="d51-kpi-strip d51-strip-warm"><i style={{width:percent(nWithTwoADL/examples.length)}}/></div></div>
   <div className="d51-kpi"><span className="d51-kpi-icon"><CalendarClock size={19}/></span><small>Recorded earlier visits</small><strong>00<em> / {examples.length}</em></strong><span>No longitudinal visits in the fixture</span><div className="d51-kpi-strip"><i style={{width:'0%'}}/></div></div>
  </section>

  <section id="examples" className="d51-explorer" aria-label="Fictional profile explorer">
   <div className="d51-patient-list"><div className="d51-card-heading"><div><span className="d51-overline">PROFILE DIRECTORY</span><h2>Individual profiles</h2></div><span className="d51-counter">{visible.length} of {examples.length}</span></div>
    <div className="d51-filter-bar" aria-label="Filter fictional examples"><button type="button" aria-pressed={filter==='all'} onClick={()=>selectFilter('all')}>All <span>{examples.length}</span></button><button type="button" aria-pressed={filter==='none'} onClick={()=>selectFilter('none')}>0 ADL <span>{nWithoutADL}</span></button><button type="button" aria-pressed={filter==='any'} onClick={()=>selectFilter('any')}>1+ ADL <span>{nWithADL}</span></button></div>
    <div className="d51-patient-buttons">{visible.map(({p,i})=><button type="button" className={'d51-patient'+(index===i?' selected':'')} key={p.id} aria-pressed={index===i} onClick={()=>setSelected(i)}>
     <span className="d51-avatar">{String(i+1).padStart(2,'0')}</span><span className="d51-patient-copy"><strong>Example {String(i+1).padStart(2,'0')}</strong><small>{p.age} years · {p.sex}</small></span><span className={'d51-adl-tag'+(p.adl_limitations>=2?' several':p.adl_limitations===1?' one':'')}>{p.adl_limitations} ADL</span><ChevronRight size={16} aria-hidden="true"/></button>)}</div>
    <p className="d51-panel-foot"><Info size={15}/> Functional counts describe the displayed fictional records, not medical priority.</p>
   </div>

   <article className="d51-detail" aria-live="polite" aria-label="Selected fictional example details">
    <div className="d51-detail-head"><div><span className="d51-overline">CURRENT / GENERATED BASELINE</span><h2>Example {String(index+1).padStart(2,'0')}</h2><p>{patient.age} years · {patient.sex} · Synthetic record</p></div><span className={'d51-functional-pill'+(patient.adl_limitations>=2?' several':patient.adl_limitations===1?' one':'')}><i/>{patient.adl_limitations===0?'0 ADL limitations':patient.adl_limitations+' ADL '+(patient.adl_limitations===1?'limitation':'limitations')}</span></div>
    <div className="d51-detail-metrics"><div><small>ADL limitations</small><strong>{patient.adl_limitations}</strong><span>Fictional baseline</span></div><div><small>Gait speed</small><strong>{value(patient.gait_speed_mps,'m/s')}</strong><span>Generated measurement</span></div><div><small>Grip strength</small><strong>{value(patient.grip_strength_kg,'kg')}</strong><span>{patient.grip_strength_kg===null?'Not available':'Generated measurement'}</span></div></div>
    <div className="d51-conditions"><div className="d51-row-label"><h3>Listed conditions</h3><span>{patient.current_conditions.length} in profile</span></div><div className="d51-tags">{patient.current_conditions.length?patient.current_conditions.map(c=><span key={c}>{c}</span>):<span>No conditions listed</span>}</div></div>
    <div className="d51-projection"><div className="d51-projection-head"><div><span className="d51-overline">ARTIFICIAL MODEL OUTPUT</span><h3>Illustrative future ADL decline</h3><p>Synthetic logistic regression · Invented two-year outcome</p></div><div className="d51-score-dial" role="img" aria-label={`Fictional model score ${percent(patient.fictional_model_probability)}`} style={{background:`conic-gradient(#218f85 0 ${patient.fictional_model_probability*100}%, #d8ece5 ${patient.fictional_model_probability*100}% 100%)`}}><span><strong>{percent(patient.fictional_model_probability)}</strong><small>model score</small></span></div></div>
     <div role="img" aria-label={`Fictional probability ${percent(patient.fictional_model_probability)} on a zero to one hundred percent scale`} className="d51-prob-track"><span style={{width:percent(patient.fictional_model_probability)}}/></div>
     <div className="d51-track-labels"><span>0%</span><span>100%</span></div>
     <div className="d51-model-foot"><span><i/> Artificial follow-up label: <b>{patient.observed_demo_outcome===1?'Decline':'No decline'}</b></span><span>Not a validated future health risk</span></div>
    </div>
    <div className="d51-empty-history"><CalendarClock size={16}/><span><strong>No earlier visits available.</strong> Only fictional baseline and artificial follow-up labels are present.</span></div>
   </article>
  </section>

  <section className="d51-distribution" aria-label="Fictional example model score comparison"><div className="d51-card-heading"><div><span className="d51-overline">ARTIFICIAL MODEL / EIGHT PROFILES</span><h2>Illustrative scores</h2></div><span className="d51-score-range">Range <b>{percent(scoreBounds.min)}–{percent(scoreBounds.max)}</b></span></div>
   <div className="d51-score-grid">{examples.map((p,i)=><button key={p.id} type="button" className={'d51-score-row'+(index===i?' selected':'')} onClick={()=>setSelected(i,true)} aria-label={`Select example ${i+1}, artificial model score ${percent(p.fictional_model_probability)}`}><span>Example {String(i+1).padStart(2,'0')}</span><span className="d51-score-track"><span style={{width:percent(p.fictional_model_probability)}}/></span><strong>{percent(p.fictional_model_probability)}</strong></button>)}</div>
   <p className="d51-chart-note">Scores come from artificial labels, not NHANES or HUNT. They are not diagnoses, clinical alerts or medical severity categories.</p>
  </section>

  <div className="d51-boundary"><Database size={17}/><strong>Population research</strong><span>Independent NHANES survey aggregates · No individual example linkage</span></div>
  <section id="population" className="d51-population" aria-label="Real NHANES population research"><div className="d51-pop-head"><div><span className="d51-overline">REAL PUBLIC SURVEY / NHANES 2015–2018</span><h2>Mobility evidence</h2><p>Current self-reported difficulty walking a quarter mile · Adults 65+</p></div><span className="d51-pop-tag"><Database size={15}/> PUBLIC AGGREGATES</span></div>
   <div className="d51-research-kpis"><div><small>2015–16 respondents</small><strong>{dev.questionnaire_respondents.toLocaleString('en-US')}</strong><span>{dev.target_events} reported difficulty</span></div><div><small>2017–18 respondents</small><strong>{later.questionnaire_respondents.toLocaleString('en-US')}</strong><span>{later.target_events} reported difficulty</span></div><div><small>Later-cycle ROC-AUC</small><strong>{mobility.evaluation.roc_auc.toFixed(3)}</strong><span>Ranking performance, not accuracy</span></div><div><small>Sensitivity (0.5 threshold)</small><strong>{percent(mobility.evaluation.sensitivity_at_0_5)}</strong><span>Low · Not a clinical screening result</span></div></div>
   <div className="d51-research-grid"><div className="d51-figure"><h3>Reported walking difficulty</h3><p>Unweighted proportions · Eligible respondents only</p>
    {[{label:'2015–16',v:dev.observed_event_fraction,n:dev.questionnaire_respondents},{label:'2017–18',v:later.observed_event_fraction,n:later.questionnaire_respondents}].map(c=><div className="d51-mobility-row" key={c.label}><div><strong>{c.label}</strong><span>n = {c.n.toLocaleString('en-US')}</span></div><div className="d51-stacked" role="img" aria-label={`${c.label}: ${percent(c.v)} reported difficulty, ${percent(1-c.v)} did not`}><span style={{width:percent(c.v)}}/><span style={{width:percent(1-c.v)}}/></div><strong>{percent(c.v)}</strong></div>)}
    <div className="d51-legend"><span><i/> Reported difficulty</span><span><i/> No reported difficulty</span></div>
   </div><div className="d51-figure"><div className="d51-figure-top"><div><h3>Six-model comparison</h3><p>Development validation Brier · Lower is better</p></div><span>Selected: {mobility.selected_model}</span></div><div className="d51-models">{mobility.models.map(m=><div className={'d51-model'+(m.name===mobility.selected_model?' chosen':'')} key={m.name}><span>{m.name==='Histogram gradient boosting'?'Histogram boosting':m.name}</span><div className="d51-model-track"><i style={{width:`${m.validation_brier/0.2*100}%`}}/></div><strong>{m.validation_brier.toFixed(4)}</strong></div>)}</div><p className="d51-chart-note">CatBoost selected by validation Brier, not universal model superiority.</p></div></div>
   <details className="d51-methods"><summary><Layers3 size={17}/> Research interpretation and limitations <ChevronRight size={17}/></summary><div><p>This real NHANES model classifies current self-reported mobility difficulty, not future frailty. The later 2017–18 evaluation was previously inspected, not a fresh untouched holdout. ROC-AUC measures ranking, not classification accuracy. Later-cycle Brier score: {mobility.evaluation.brier.toFixed(3)}. Sensitivity at threshold 0.5 is low; this model is not a clinical screening tool.</p><p>Fractions are unweighted and not nationally representative. Two survey cycles involve different individuals. No HUNT access or validation is claimed. No real person-level survey records, predictions or fitted model are hosted.</p></div></details>
  </section>
  <footer className="d51-bottom"><div><span className="d51-bottom-icon"><ShieldCheck size={19}/></span><div><strong>Detailed research workspace</strong><p>Assessment instruments, study methods and historical model analyses.</p></div></div><Link href="/doctor/workspace">Open detailed workspace <ArrowRight size={16}/></Link></footer>
 </main>;
}
