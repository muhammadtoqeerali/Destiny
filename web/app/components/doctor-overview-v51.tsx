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
const dev=mobility.cohorts['2015-2016'];
const later=mobility.cohorts['2017-2018'];

/** Two explicitly independent display layers: synthetic people and real *aggregate* mobility research. */
export function DoctorOverviewV51(){
 const [index,setIndex]=useState(0);
 const patient=examples[index]; // This is a generated example, NEVER a participant or real patient.
 return <main className="page-wrap d51" aria-label="Doctor overview">
  <header className="d51-hero">
   <div><span className="d51-kicker"><HeartPulse size={15}/> FRAILTYSCOPE / DOCTOR OVERVIEW</span>
    <h1>Health at a glance<span>.</span></h1>
    <p>Understand the present picture, explore individual examples, and see what the research can—and cannot—tell us.</p>
    <div className="d51-hero-links"><a href="#examples">Explore examples <ArrowRight size={16}/></a><a href="#population">View population research <BarChart3 size={16}/></a></div>
   </div>
   <aside className="d51-hero-aside"><span className="d51-aside-mark"><ShieldCheck size={20}/></span><strong>Demonstration environment</strong><span>Invented people only. No live records, diagnoses, clinical alerts, or patient-level predictions.</span></aside>
  </header>

  <div className="d51-section-title"><div><span className="d51-overline">01 / FICTIONAL EXAMPLES</span><h2>Current example overview</h2></div><span className="d51-source">SIMULATED DATA · NOT HUNT</span></div>
  <section className="d51-kpis" aria-label="Fictional cohort summary">
   <div className="d51-kpi"><span className="d51-kpi-icon"><Users size={19}/></span><small>Example profiles</small><strong>{examples.length.toString().padStart(2,'0')}</strong><span>Selected from {demo.configuration.generation_n.toLocaleString('en-US')} generated rows</span></div>
   <div className="d51-kpi"><span className="d51-kpi-icon"><Activity size={19}/></span><small>With any ADL limitation</small><strong>{nWithADL.toString().padStart(2,'0')}<em> / {examples.length}</em></strong><span>Generated baseline observations</span></div>
   <div className="d51-kpi"><span className="d51-kpi-icon"><ClipboardList size={19}/></span><small>With 2+ ADL limitations</small><strong>{nWithTwoADL.toString().padStart(2,'0')}<em> / {examples.length}</em></strong><span>Descriptive, not clinical priority</span></div>
   <div className="d51-kpi"><span className="d51-kpi-icon"><CalendarClock size={19}/></span><small>Recorded prior visits</small><strong>00</strong><span>No visit histories are in this fixture</span></div>
  </section>

  <section id="examples" className="d51-explorer" aria-label="Fictional profile explorer">
   <div className="d51-patient-list"><div className="d51-card-heading"><div><span className="d51-overline">EXAMPLE SELECTOR</span><h2>Individual profiles</h2></div><span className="d51-counter">{examples.length} examples</span></div>
    <div className="d51-patient-buttons">{examples.map((p,i)=><button type="button" className={'d51-patient'+(index===i?' selected':'')} key={p.id} aria-pressed={index===i} onClick={()=>setIndex(i)}>
     <span className="d51-avatar">{String(i+1).padStart(2,'0')}</span><span className="d51-patient-copy"><strong>Example {String(i+1).padStart(2,'0')}</strong><small>{p.age} years · {p.sex}</small></span><span className="d51-patient-sub">{p.adl_limitations} ADL {p.adl_limitations===1?'limit':'limits'}</span><ChevronRight size={16} aria-hidden="true"/></button>)}</div>
    <p className="d51-panel-foot"><Info size={15}/> Profiles are invented; the counts are not population estimates.</p>
   </div>

   <article className="d51-detail" aria-live="polite" aria-label="Selected fictional example details">
    <div className="d51-detail-head"><div><span className="d51-overline">GENERATED HEALTH SNAPSHOT</span><h2>Example {String(index+1).padStart(2,'0')}</h2><p>{patient.age} years · {patient.sex} · fictional baseline</p></div><span className="d51-verified">SIMULATED</span></div>
    <div className="d51-detail-metrics"><div><small>ADL limitations</small><strong>{patient.adl_limitations}</strong><span>At generated baseline</span></div><div><small>Gait speed</small><strong>{value(patient.gait_speed_mps,'m/s')}</strong><span>Invented measurement</span></div><div><small>Grip strength</small><strong>{value(patient.grip_strength_kg,'kg')}</strong><span>Invented measurement</span></div></div>
    <div className="d51-conditions"><div className="d51-row-label"><h3>Conditions in example</h3><span>{patient.current_conditions.length} listed</span></div><div className="d51-tags">{patient.current_conditions.length?patient.current_conditions.map(c=><span key={c}>{c}</span>):<span>None included in this example</span>}</div></div>
    <div className="d51-projection"><div className="d51-projection-head"><div><span className="d51-overline">ARTIFICIAL MODEL OUTPUT</span><h3>Illustrative future ADL decline</h3></div><strong>{percent(patient.fictional_model_probability)}</strong></div>
     <div role="img" aria-label={`Fictional model score ${percent(patient.fictional_model_probability)} on a zero to one hundred percent scale`} className="d51-prob-track"><span style={{width:percent(patient.fictional_model_probability)}}/></div>
     <div className="d51-track-labels"><span>0%</span><span>100%</span></div>
     <p>Generated by a logistic model trained on artificial outcomes. <b>Not a validated future health risk</b> or a recommendation for care.</p>
    </div>
    <div className="d51-timeline"><h3>Available example history</h3><div className="d51-time-items"><div><span className="d51-time-dot"/><strong>Generated baseline</strong><small>Current measurements and conditions shown above</small></div><div><span className="d51-time-dot hollow"/><strong>Artificial two-year outcome</strong><small>Invented label: {patient.observed_demo_outcome===1?'ADL decline':'no ADL decline'}. Not an observed visit.</small></div></div><div className="d51-empty-history"><CalendarClock size={16}/> No earlier visits or longitudinal medical records exist for this example.</div></div>
   </article>
  </section>

  <section className="d51-distribution" aria-label="Fictional example model score comparison"><div className="d51-card-heading"><div><span className="d51-overline">SIDE-BY-SIDE / SYNTHETIC</span><h2>How the eight example scores differ</h2></div><span className="d51-source">ARTIFICIAL MODEL</span></div>
   <div className="d51-score-grid">{examples.map((p,i)=><button key={p.id} type="button" className={'d51-score-row'+(index===i?' selected':'')} onClick={()=>{setIndex(i);document.getElementById('examples')?.scrollIntoView({behavior:'auto',block:'start'});}} aria-label={`Select example ${i+1}, artificial model score ${percent(p.fictional_model_probability)}`}><span>Example {String(i+1).padStart(2,'0')}</span><span className="d51-score-track"><span style={{width:percent(p.fictional_model_probability)}}/></span><strong>{percent(p.fictional_model_probability)}</strong></button>)}</div>
   <p className="d51-chart-note">Scores describe the demonstration model only; higher numbers are not emergency categories. Select any row to view that profile.</p>
  </section>

  <section id="population" className="d51-population" aria-label="Real NHANES population research"><div className="d51-pop-head"><div><span className="d51-overline">02 / REAL PUBLIC SURVEY · SEPARATE DATA SOURCE</span><h2>What the NHANES mobility data show</h2><p>Adults aged 65+ reporting <b>current difficulty walking a quarter mile</b>. This is a different dataset and task from the fictional future examples above.</p></div><span className="d51-pop-tag"><Database size={15}/> REAL AGGREGATES</span></div>
   <div className="d51-research-kpis"><div><small>Participants · 2015–16</small><strong>{dev.questionnaire_respondents.toLocaleString('en-US')}</strong><span>{dev.target_events} reported difficulty</span></div><div><small>Participants · 2017–18</small><strong>{later.questionnaire_respondents.toLocaleString('en-US')}</strong><span>{later.target_events} reported difficulty</span></div><div><small>Later-cycle ROC-AUC</small><strong>{mobility.evaluation.roc_auc.toFixed(3)}</strong><span>Discrimination, not accuracy</span></div><div><small>Later-cycle sensitivity</small><strong>{percent(mobility.evaluation.sensitivity_at_0_5)}</strong><span>At 0.5 threshold · low</span></div></div>
   <div className="d51-research-grid"><div className="d51-figure"><h3>Reported walking difficulty</h3><p>Unweighted fractions of eligible survey respondents</p>
    {[{label:'2015–16',v:dev.observed_event_fraction,n:dev.questionnaire_respondents},{label:'2017–18',v:later.observed_event_fraction,n:later.questionnaire_respondents}].map(c=><div className="d51-mobility-row" key={c.label}><div><strong>{c.label}</strong><span>n = {c.n.toLocaleString('en-US')}</span></div><div className="d51-stacked" role="img" aria-label={`${c.label}: ${percent(c.v)} reported difficulty, ${percent(1-c.v)} did not`}><span style={{width:percent(c.v)}}/><span style={{width:percent(1-c.v)}}/></div><strong>{percent(c.v)}</strong></div>)}
    <div className="d51-legend"><span><i/> Reported difficulty</span><span><i/> No reported difficulty</span></div>
   </div><div className="d51-figure"><div className="d51-figure-top"><div><h3>Six-model comparison</h3><p>Development validation Brier score · lower is better</p></div><span>Selected: {mobility.selected_model}</span></div><div className="d51-models">{mobility.models.map(m=><div className={'d51-model'+(m.name===mobility.selected_model?' chosen':'')} key={m.name}><span>{m.name==='Histogram gradient boosting'?'Histogram boosting':m.name}</span><div className="d51-model-track"><i style={{width:`${m.validation_brier/0.2*100}%`}}/></div><strong>{m.validation_brier.toFixed(4)}</strong></div>)}</div><p className="d51-chart-note">CatBoost was chosen by validation Brier score, not by cross-validation superiority.</p></div></div>
   <details className="d51-methods"><summary><Layers3 size={17}/> Research interpretation and limitations <ChevronRight size={17}/></summary><div><p>The real model classifies <b>current self-reported mobility difficulty</b>; it does not forecast future frailty. The later-cycle evaluation (2017–18) was previously inspected, not a fresh untouched holdout. ROC-AUC {mobility.evaluation.roc_auc.toFixed(3)} measures ranking ability, not the percentage correctly classified. Brier {mobility.evaluation.brier.toFixed(3)}; 0.5-threshold sensitivity is low and is not suitable as a screening claim.</p><p>Fractions here are unweighted, not nationally representative estimates. The two NHANES survey cycles contain different respondents. No person-level NHANES data or fitted real model is hosted. No HUNT access or validation is claimed.</p></div></details>
  </section>
  <footer className="d51-bottom"><div><span className="d51-bottom-icon"><ShieldCheck size={19}/></span><div><strong>Explore more, without clutter.</strong><p>The original technical Doctor workspace remains available for in-depth research demonstrations.</p></div></div><Link href="/doctor/workspace">Open detailed workspace <ArrowRight size={16}/></Link></footer>
 </main>;
}
