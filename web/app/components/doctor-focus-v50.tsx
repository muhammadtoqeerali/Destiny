'use client';

import {useMemo, useState} from 'react';
import Link from 'next/link';
import {Activity, ArrowRight, BarChart3, Check, ChevronDown, ChevronRight, CircleAlert, Footprints, HeartPulse, Info, ShieldCheck, Users} from 'lucide-react';
import mobility from '../data/real-mobility-summary-v49.json';
import demonstration from '../data/interview-benchmark-v47.json';

const cases = demonstration.fictional_examples;
const number = (n:number) => n.toLocaleString('en-US');
const percent = (n:number,d=1) => `${(n*100).toFixed(d)}%`;
const formatMetric = (n:number|null,unit='') => n === null ? 'Not recorded' : `${n}${unit}`;

// These are DEMONSTRATION display ranges, not medical categories or triage thresholds.
const category = (p:number) => p >= .6 ? 'Higher demo score' : p >= .3 ? 'Middle demo score' : 'Lower demo score';
const tone = (p:number) => p >= .6 ? 'high' : p >= .3 ? 'mid' : 'low';

export function DoctorFocusV50(){
 const [selected,setSelected]=useState(0);
 const [details,setDetails]=useState(false);
 const ordered=useMemo(()=>cases.map((p,i)=>({p,i})).sort((a,b)=>b.p.fictional_model_probability-a.p.fictional_model_probability),[]);
 const chosen=cases[selected];
 const fraction=chosen.fictional_model_probability;
 const surveyed=mobility.cohorts['2017-2018'];
 const development=mobility.cohorts['2015-2016'];
 const higher=cases.filter(p=>p.fictional_model_probability>=.6).length;
 const middle=cases.filter(p=>p.fictional_model_probability>=.3&&p.fictional_model_probability<.6).length;
 const limited=cases.filter(p=>p.adl_limitations>0).length;
 const contributions=[...chosen.illustrative_factors].sort((a,b)=>Math.abs(b.log_odds_contribution)-Math.abs(a.log_odds_contribution));
 return <main className="focus-app focus-doctor" id="main">
  <div className="focus-container">
   <div className="focus-page-heading"><div><p className="focus-eyebrow"><HeartPulse size={15}/> CLINICAL INSIGHTS</p><h1>Understand the person.<br/><em>See the whole picture.</em></h1><p className="focus-lead">A clear view of older-adult mobility research and fictional health journeys, with evidence and illustrations kept separate.</p></div><div className="focus-heading-aside"><ShieldCheck size={20}/><span><strong>Research demonstration</strong><small>No real patient records or clinical predictions</small></span></div></div>

   <section className="focus-survey-section" aria-labelledby="population-title">
    <div className="focus-section-intro"><div><span className="focus-section-label">01 / POPULATION EVIDENCE</span><h2 id="population-title">What the real survey tells us</h2><p>Current self-reported difficulty walking a quarter mile among eligible NHANES respondents aged 65+.</p></div><span className="focus-source-chip"><span/> Real NHANES data</span></div>
    <div className="focus-pop-grid">
      <article className="focus-pop-primary"><div className="focus-card-kicker"><Footprints size={18}/> LATER SURVEY · 2017–18</div><div className="focus-pop-number">{percent(surveyed.observed_event_fraction)}<span>reported difficulty</span></div><div className="focus-progress" aria-label={`${percent(surveyed.observed_event_fraction)} reported walking difficulty`} role="img"><span style={{width:percent(surveyed.observed_event_fraction)}}/></div><div className="focus-pop-bottom"><b>{number(surveyed.target_events)} of {number(surveyed.questionnaire_respondents)}</b><span>respondents in the eligible study subset</span></div></article>
      <article className="focus-pop-secondary"><div className="focus-small-head"><span className="focus-card-kicker">EARLIER SURVEY · 2015–16</span><span className="focus-mini-icon"><Users size={17}/></span></div><strong>{percent(development.observed_event_fraction)}</strong><p>Reported the same walking difficulty in the earlier eligible subset.</p><div className="focus-secondary-foot">{number(development.target_events)} of {number(development.questionnaire_respondents)} respondents</div></article>
      <article className="focus-pop-secondary focus-performance"><div className="focus-small-head"><span className="focus-card-kicker">MODEL DISCRIMINATION</span><span className="focus-mini-icon"><BarChart3 size={17}/></span></div><strong>{mobility.evaluation.roc_auc.toFixed(3)}</strong><p>Later-cycle ROC-AUC: how well the model ranks respondents who did and did not report difficulty.</p><div className="focus-secondary-foot">Exploratory · later cycle previously inspected</div></article>
    </div>
    <p className="focus-subnote"><Info size={15}/> Survey fractions are unweighted within the eligible study subsets, not US national prevalence. The fitted NHANES model classifies <strong>current</strong> walking difficulty—not future frailty.</p>
   </section>

   <section className="focus-people-section" aria-labelledby="cases-title">
    <div className="focus-section-intro"><div><span className="focus-section-label">02 / ILLUSTRATIVE CASE EXPLORER</span><h2 id="cases-title">A more complete view of an older adult</h2><p>Browse eight invented profiles to see health history, current measures and a model-generated future illustration.</p></div><span className="focus-source-chip focus-source-fiction"><span/> Fictional examples only</span></div>
    <div className="focus-summary-grid" role="group" aria-label="Fictional profile overview">
      <div className="focus-summary-card"><span>Example profiles</span><strong>{cases.length.toString().padStart(2,'0')}</strong><small>Generated, not patients</small><Users size={22}/></div>
      <div className="focus-summary-card"><span>Higher demo scores</span><strong>{higher.toString().padStart(2,'0')}</strong><small>Display range ≥60% · not urgency</small><Activity size={22}/></div>
      <div className="focus-summary-card"><span>Middle demo scores</span><strong>{middle.toString().padStart(2,'0')}</strong><small>Display range 30–59%</small><BarChart3 size={22}/></div>
      <div className="focus-summary-card"><span>With activity limitations</span><strong>{limited.toString().padStart(2,'0')}</strong><small>Reported in fictional baselines</small><Footprints size={22}/></div>
    </div>

    <div className="focus-case-layout">
     <aside className="focus-case-rail" aria-label="Fictional profile selection"><div className="focus-rail-title"><b>Example profiles</b><span>By demo score</span></div><div className="focus-case-list">{ordered.map(({p,i})=><button type="button" key={p.id} className={`focus-case-row ${i===selected?'active':''}`} aria-pressed={i===selected} onClick={()=>{setSelected(i);setDetails(false)}}><span className="focus-case-avatar">{String(i+1).padStart(2,'0')}</span><span className="focus-case-meta"><strong>Example {i+1}</strong><small>{p.age} years · {p.sex} · {p.adl_limitations} ADL limits</small></span><span className={`focus-mini-score ${tone(p.fictional_model_probability)}`}>{percent(p.fictional_model_probability,0)}</span><ChevronRight size={16}/></button>)}</div><p className="focus-rail-foot"><CircleAlert size={14}/> Scores rank invented examples; they do not identify urgent medical cases.</p></aside>

     <article className="focus-case-detail" aria-live="polite" aria-label="Selected fictional profile">
      <div className="focus-detail-header"><div><div className="focus-case-badge">FICTIONAL PROFILE · {chosen.id}</div><h3>Example {selected+1} <span>{chosen.age} years · {chosen.sex}</span></h3></div><span className="focus-illustrative-badge">Illustration, not a patient</span></div>
      <div className="focus-story" aria-label="Illustrative health journey">
       <div className="focus-story-step"><div className="focus-story-marker"><Check size={15}/></div><div className="focus-story-body"><div className="focus-story-heading"><span>01</span><h4>Health history available</h4></div><p>Conditions represented in this fictional baseline, not a sequence of previous visits.</p><div className="focus-condition-list">{chosen.current_conditions.length?chosen.current_conditions.map(c=><span key={c}>{c}</span>):<span>No conditions listed</span>}</div><p className="focus-missing-history">Earlier dated visit records: <strong>not available in this demonstrator.</strong></p></div></div>
       <div className="focus-story-step"><div className="focus-story-marker"><Activity size={15}/></div><div className="focus-story-body"><div className="focus-story-heading"><span>02</span><h4>Current fictional snapshot</h4></div><div className="focus-vitals"><div><span>Daily-activity limits</span><strong>{chosen.adl_limitations}</strong></div><div><span>Walking speed</span><strong>{formatMetric(chosen.gait_speed_mps,' m/s')}</strong></div><div><span>Grip strength</span><strong>{formatMetric(chosen.grip_strength_kg,' kg')}</strong></div></div></div></div>
       <div className="focus-story-step focus-future-step"><div className="focus-story-marker"><ArrowRight size={15}/></div><div className="focus-story-body"><div className="focus-story-heading"><span>03</span><h4>Illustrative future outcome</h4></div><div className="focus-forecast"><div className="focus-forecast-content"><small>SYNTHETIC MODEL OUTPUT</small><strong>{percent(fraction)}</strong><span className={`focus-forecast-band ${tone(fraction)}`}>{category(fraction)}</span><p>Invented next-period daily-activity decline score. <b>Not a clinical risk estimate.</b></p></div><div className="focus-ring" style={{'--ring-pct':percent(fraction)} as React.CSSProperties} role="img" aria-label={`Fictional model score ${percent(fraction)}`}><span>DEMO</span></div></div><div className="focus-demo-outcome"><Check size={14}/> Invented follow-up label: <b>{chosen.observed_demo_outcome===1?'decline':'no decline'}</b>. This is a generated outcome, not a patient observation.</div></div></div>
      </div>
      <div className="focus-factors-box"><button type="button" onClick={()=>setDetails(x=>!x)} aria-expanded={details} className="focus-disclosure"><span><BarChart3 size={18}/> What shaped this illustrative score?</span><ChevronDown size={18} className={details?'rotated':''}/></button>{details&&<div className="focus-factors-body"><p>Shown are the largest transformed-feature contributions to the <b>fictional logistic model's log-odds</b>. They do not describe clinical causes.</p>{contributions.map(f=><div className="focus-factor" key={f.feature}><span>{f.feature.replaceAll('_',' ')}</span><div className="focus-factor-track"><i className={f.log_odds_contribution>=0?'positive':'negative'} style={{width:`${Math.min(100,Math.abs(f.log_odds_contribution)/.65*100)}%`}}/></div><strong>{f.log_odds_contribution>=0?'+':''}{f.log_odds_contribution.toFixed(2)}</strong></div>)}<p className="focus-factors-limit">Real NHANES model explanations are presented separately in Research. No generated profile is scored by the real model.</p></div>}</div>
     </article>
    </div>
    <div className="focus-next-step"><div><span>GO DEEPER</span><h3>From clear patient stories to reproducible model evidence.</h3><p>See the dataset, candidate models, calibration and model reliance behind the real population analysis.</p></div><Link href="/admin">Explore research evidence <ArrowRight size={17}/></Link></div>
   </section>
  </div>
 </main>
}
