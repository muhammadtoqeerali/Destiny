'use client';

import {useState} from 'react';
import {ArrowRight, ArrowUpRight, CheckCircle2, CircleHelp, ClipboardList, GitBranch, HeartPulse, LockKeyhole, Pause, Play, ShieldCheck, Sparkles} from 'lucide-react';

type Profile = Record<string,string>;
type Visit = {id:number; date:string; bmi:number|null; phq:number|null};
type Feature={label:string; value:string; state:'recorded'|'unrecorded'|'status'};
const nameByKey:Record<string,string>={
 age:'Age',sex:'Sex',bmi:'BMI',phq9_score:'PHQ-9',walking_difficulty:'Walking',
 stairs_difficulty:'Stairs',stooping_difficulty:'Stooping',heart_failure:'Heart failure',
 coronary_disease:'Coronary disease',stroke:'Stroke',cancer:'Cancer',diabetes:'Diabetes',
 hypertension:'Hypertension',ever_smoked:'Smoking history'
};
const special=new Set(['Does not do activity','Not asked (structural skip)','Refused',"Don't know"]);
const isValid=(key:string,value:string)=>{
 if(!value)return false;
 const n=Number(value);
 if(key==='age')return Number.isInteger(n)&&n>=65&&n<=110;
 if(key==='bmi')return Number.isFinite(n)&&n>=10&&n<=70;
 if(key==='phq9_score')return Number.isInteger(n)&&n>=0&&n<=27;
 return Object.prototype.hasOwnProperty.call(nameByKey,key);
};
function features(profile:Profile):Feature[]{
 return Object.entries(nameByKey).map(([key,label])=>{
  const value=profile[key]||'';
  return {label,value:isValid(key,value)?value:'Not recorded',state:!isValid(key,value)?'unrecorded':special.has(value)?'status':'recorded'};
 });
}
const measured=(visits:readonly Visit[],key:'bmi'|'phq')=>visits.filter(v=>v[key]!==null).sort((a,b)=>a.date.localeCompare(b.date));
function Delta({visits,metric,label,units}:{visits:readonly Visit[];metric:'bmi'|'phq';label:string;units:string}){
 const m=measured(visits,metric);
 if(m.length<2)return <div className="v36-delta"><span>{label}</span><strong>Not enough visits</strong><small>Two dated measurements are needed to compare.</small></div>;
 const first=m[0][metric]!,last=m[m.length-1][metric]!;
 const difference=last-first;
 return <div className="v36-delta"><span>{label}</span><strong>{difference>0?'+':''}{difference.toFixed(1)} {units}</strong><small>{m[0].date} → {m[m.length-1].date} · observed change only</small></div>;
}

/** Live descriptive browser-only readout. Never exports data or computes clinical scores. */
export function DoctorJourneyV36({profile,visits,onViewFollowUp}:{profile:Profile;visits:readonly Visit[];onViewFollowUp:()=>void}){
 const list=features(profile);
 const count=list.filter(f=>f.state!=='unrecorded').length;
 const statuses=list.filter(f=>f.state==='status');
 return <section className="v36-assessment" aria-labelledby="v36-assessment-title">
  <div className="v36-brief-top"><span className="v36-kicker"><Sparkles size={15} aria-hidden="true"/> LIVE ASSESSMENT WORKSPACE</span><span className="v36-local"><LockKeyhole size={15} aria-hidden="true"/> Browser session only</span></div>
  <div className="v36-brief-grid"><div>
    <h3 id="v36-assessment-title">Your entries become a live health snapshot.</h3>
    <p>As you complete the form, recorded observations appear here. You can reuse BMI and PHQ-9 in a dated follow-up visit. This is not a prediction, diagnosis or assessment of future risk.</p>
    <div className="v36-capsules" aria-label="Live entered fields">
      {list.filter(f=>f.state!=='unrecorded').length===0?<span className="v36-empty-chip">No valid observations entered yet</span>:
       list.filter(f=>f.state!=='unrecorded').map(f=><span className={f.state==='status'?'v36-chip v36-chip-status':'v36-chip'} key={f.label}><b>{f.label}</b>{f.value}</span>)}
    </div>
    {statuses.length>0&&<p className="v36-status-note"><CircleHelp size={16} aria-hidden="true"/> Nonparticipation, structural skips and nonresponse remain separate statuses; they are not interpreted as difficulty.</p>}
    <button type="button" className="v36-action" onClick={onViewFollowUp}>Open follow-up measurements <ArrowRight size={16} aria-hidden="true"/></button>
  </div><aside className="v36-readiness"><span>DATA COMPLETENESS</span><strong>{count} <small>/ 14</small></strong>
    <div className="v36-readiness-meter" role="progressbar" aria-label="Recorded observation fields" aria-valuemin={0} aria-valuemax={14} aria-valuenow={count}><i style={{width:`${100*count/14}%`}}/></div>
    <p>14 descriptive fields available for entry; this is not a measure of clinical suitability or model readiness.</p>
    <div className="v36-readiness-divider"/><b><ShieldCheck size={16} aria-hidden="true"/> Individual inference not enabled</b><small>No model is fitted, loaded or queried from this public form.</small>
  </aside></div>
 </section>;
}

export function FollowUpSummaryV36({visits}:{visits:readonly Visit[]}){
 return <section className="v36-follow" aria-label="Observed measurement comparisons">
  <div className="v36-follow-head"><div><span className="v36-kicker">LINKED INSIDE THIS SESSION</span><h3>Track observed changes, not predicted outcomes.</h3></div><span>{visits.length} visit{visits.length===1?'':'s'} entered</span></div>
  <div className="v36-deltas"><Delta visits={visits} metric="bmi" label="BMI change" units="kg/m²"/><Delta visits={visits} metric="phq" label="PHQ-9 change" units="points"/></div>
  <p>Visits entered here are not retrieved from NHANES or a health-record system. They exist only in memory in this open browser tab, and disappear on reload.</p>
 </section>;
}

const stages=[
 {title:'Observations arrive',sub:'The form supplies values',body:'Age, symptoms, mobility and recorded history arrive as separate fields. Watch how the entered values are represented; nothing is sent to a prediction server.',symbol:'01'},
 {title:'Meaning is preserved',sub:'Missing does not mean healthy',body:'A structural skip, an unanswered question, an explicit “No”, and observed physical difficulty are different kinds of information. Software must not collapse them.',symbol:'02'},
 {title:'A model learns from approved research',sub:'Training and evaluation are separate',body:'In a properly authorized study, training data can inform a model and held-out data can test its reliability. The historical NHANES development experiment cannot be repeated or used for new patient inference here.',symbol:'03'},
 {title:'An explanation accompanies a real estimate',sub:'Contributions need a real trained model',body:'A genuine explanation would display a validated prediction alongside model-specific feature contributions, uncertainty and limitations. This page cannot invent contributions from generic rules or from a historical aggregate AUC.',symbol:'04'},
 {title:'A research gate protects the person',sub:'No authorized individual prediction',body:'The original case has a provisional prediction index, incomplete source mapping and a previously inspected later cycle. Approval, appropriate evaluation, and a governed inference service are needed before any personalized forecast.',symbol:'05'},
];
export function PredictionStoryV36({profile}:{profile:Profile}){
 const [step,setStep]=useState(0);
 const [animate,setAnimate]=useState(true);
 const entered=features(profile).filter(f=>f.state!=='unrecorded').slice(0,5);
 const state=stages[step];
 return <section className="v36-theater" aria-label="Animated explanation of an ML workflow">
  <div className="v36-theater-head"><div><span className="v36-kicker">INTERACTIVE EXPLANATION · EDUCATIONAL</span><h3>From an observation to a responsible explanation</h3><p>Choose each stage to see what a trustworthy predictive workflow would need to do. No patient prediction is calculated.</p></div>
   <button className="v36-pause" type="button" aria-pressed={!animate} onClick={()=>setAnimate(x=>!x)}>{animate?<Pause size={16}/>:<Play size={16}/>} {animate?'Pause motion':'Resume motion'}</button></div>
  <div className={`v36-visual ${animate?'v36-is-playing':'v36-is-paused'}`}>
    <div className="v36-river" aria-hidden="true"><span className="v36-particle a"/><span className="v36-particle b"/><span className="v36-particle c"/></div>
    <div className="v36-machine-grid">
      <div className={step===0?'v36-machine active':'v36-machine'}><ClipboardList size={25} aria-hidden="true"/><small>INPUT</small><strong>Observations</strong><span>{entered.length ? `${entered.length} entered field previews`:'No entered values yet'}</span></div>
      <div className={step===1?'v36-machine active':'v36-machine'}><GitBranch size={25} aria-hidden="true"/><small>CHECKS</small><strong>Meaning & quality</strong><span>Preserve missingness and timing</span></div>
      <div className={step===2?'v36-machine active':'v36-machine'}><HeartPulse size={25} aria-hidden="true"/><small>RESEARCH</small><strong>Trained model</strong><span>Historical studies, not a live service</span></div>
      <div className={step>=3?'v36-machine active':'v36-machine'}><ShieldCheck size={25} aria-hidden="true"/><small>GATE</small><strong>Explanation</strong><span>Individual inference blocked</span></div>
    </div>
  </div>
  <div className="v36-preview"><span>VALUES VISIBLE IN THIS BROWSER</span><div>{entered.length?entered.map(f=><span key={f.label}>{f.label}: <b>{f.value}</b></span>):<span>Enter fictional or de-identified observations in Patient Assessment to see values here.</span>}</div></div>
  <div className="v36-stage-nav" aria-label="Explainability stages">{stages.map((s,i)=><button key={s.symbol} type="button" aria-current={step===i?'step':undefined} className={step===i?'active':''} onClick={()=>setStep(i)}><small>{s.symbol}</small>{s.title}</button>)}</div>
  <div className="v36-stage-detail" key={step}><div><span>STEP {state.symbol} / 05</span><h4>{state.title}</h4><strong>{state.sub}</strong><p>{state.body}</p></div><div className="v36-step-actions"><button type="button" disabled={step===0} onClick={()=>setStep(x=>x-1)}>Previous</button><button type="button" disabled={step===4} onClick={()=>setStep(x=>x+1)}>Next step <ArrowUpRight size={16} aria-hidden="true"/></button></div></div>
  <div className="v36-theater-foot"><CheckCircle2 size={17} aria-hidden="true"/><p>This is an animated explanation of the research process, <strong>not an actual explanation of a patient-specific prediction</strong>. Genuine feature effects require the exact fitted model, supported features, calibrated evaluation and independently reviewable methods. Technical historical metrics remain available in Admin.</p></div>
 </section>;
}
