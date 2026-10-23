'use client';

import {useMemo, useState} from 'react';
import {Activity, ArrowRight, CheckCircle2, Info, LockKeyhole, RotateCcw, ShieldAlert, SlidersHorizontal} from 'lucide-react';

type Profile=Record<string,string>;
const reasons=[
  'NHANES case: BLOCKED_FOR_NEW_ANALYSIS; clinical use is not approved.',
  'Original prediction index remains provisional; 11 of 14 reviewed predictors are not source-mapped.',
  'The later survey cycle was previously inspected, so it is not fresh independent validation.',
  'No approved, calibrated, securely served patient-level model is registered.',
];
const numeric=(s:string,min:number,max:number,integer:boolean)=>{
  if(s.trim()==='')return false;
  const n=Number(s);
  return Number.isFinite(n)&&n>=min&&n<=max&&(!integer||Number.isInteger(n));
};

/** Hard fail-closed release state. This does not call or load any clinical model. */
export function InferenceReadinessV37({profile,onExplore}:{profile:Profile;onExplore:()=>void}){
  const counts=Object.values(profile).filter(x=>x!==''&&x!==undefined).length;
  const invalid=[
    ['age',65,110,true],['bmi',10,70,false],['phq9_score',0,27,true],
  ].filter(([key,min,max,integer])=>{
    const value=profile[String(key)]||'';
    return value!==''&&!numeric(value,Number(min),Number(max),Boolean(integer));
  }).length;
  return <section className="v37-readiness" aria-label="Live model availability">
    <div className="v37-readiness-top">
      <div><span className="v37-overline"><Activity size={15} aria-hidden="true"/> INFERENCE READINESS</span>
        <h3>Assessment preview. Patient prediction not enabled.</h3>
        <p>The form updates descriptively, but this release has no authorized model for predicting an individual's future health or mortality.</p>
      </div>
      <div className="v37-locked"><LockKeyhole size={17} aria-hidden="true"/> Clinical inference blocked</div>
    </div>
    <div className="v37-readiness-metrics">
      <div><strong>{counts}</strong><span>fields currently entered</span></div>
      <div><strong>{invalid}</strong><span>out-of-range numeric fields</span></div>
      <div><strong>0</strong><span>patient predictions generated</span></div>
    </div>
    <details className="v37-reasons"><summary>Why is the model unavailable?</summary><ul>{reasons.map(r=><li key={r}>{r}</li>)}</ul></details>
    <div className="v37-readiness-bottom"><span><ShieldAlert size={16} aria-hidden="true"/> No entered values are transmitted, persisted or used to infer a health outcome.</span><button type="button" onClick={onExplore}>Explore a fictional scoring example <ArrowRight size={16} aria-hidden="true"/></button></div>
  </section>;
}

type Factor={name:string;contribution:number;explanation:string};
const BASE=-0.55;
const sigmoid=(z:number)=>1/(1+Math.exp(-z));
const safeFixed=(n:number)=>(n>=0?'+':'')+n.toFixed(3);
/** Educational transparent formula with invented coefficients. Not fitted to NHANES or any people. */
function exampleMath(age:number,bmi:number,mobility:number){
  const factors:Factor[]=[
    {name:'Fictional age',contribution:(age-75)*0.035,explanation:'(age − 75) × 0.035'},
    {name:'Fictional BMI',contribution:(bmi-26)*0.08,explanation:'(BMI − 26) × 0.08'},
    {name:'Fictional movement signal',contribution:[-0.40,0.15,0.65][mobility],explanation:'invented category weight'},
  ];
  const logit=BASE+factors.reduce((a,b)=>a+b.contribution,0);
  return {factors,logit,score:sigmoid(logit)};
}
export function FictionalScoringLabV37(){
  const [age,setAge]=useState(75);
  const [bmi,setBmi]=useState(26);
  const [mobility,setMobility]=useState(0);
  const data=useMemo(()=>exampleMath(age,bmi,mobility),[age,bmi,mobility]);
  const score=Math.round(data.score*1000)/10;
  const reset=()=>{setAge(75);setBmi(26);setMobility(0);};
  return <section className="v37-lab" aria-label="Fictional model calculation laboratory">
    <header className="v37-lab-head"><div><span className="v37-overline"><SlidersHorizontal size={16} aria-hidden="true"/> INTERACTIVE MATHEMATICAL DEMONSTRATION</span><h3>Change the example. See how the model math responds.</h3><p>A real-time logistic calculation with explicitly invented coefficients. These fictional inputs are separate from Patient Assessment: real patient details never enter this calculation.</p></div><div className="v37-synthetic-stamp">SYNTHETIC / NOT CLINICAL</div></header>
    <div className="v37-lab-grid">
      <div className="v37-lab-controls">
        <h4>01 / Fictional input signals</h4>
        <label htmlFor="v37-age">Fictional age <output htmlFor="v37-age">{age}</output></label><input id="v37-age" aria-label="Fictional age" type="range" min="65" max="95" value={age} onChange={e=>setAge(Number(e.target.value))}/>
        <label htmlFor="v37-bmi">Fictional BMI <output htmlFor="v37-bmi">{bmi.toFixed(1)}</output></label><input id="v37-bmi" aria-label="Fictional BMI" type="range" min="18" max="40" step="0.5" value={bmi} onChange={e=>setBmi(Number(e.target.value))}/>
        <label htmlFor="v37-movement">Fictional movement category</label><select id="v37-movement" aria-label="Fictional movement category" value={mobility} onChange={e=>setMobility(Number(e.target.value))}><option value={0}>Illustrative signal A</option><option value={1}>Illustrative signal B</option><option value={2}>Illustrative signal C</option></select>
        <button type="button" className="v37-reset" onClick={reset}><RotateCcw size={15} aria-hidden="true"/> Reset fictional example</button>
        <p className="v37-lab-small"><Info size={15} aria-hidden="true"/> Input ranges and weights are invented for education. Their sizes and directions do not describe the effects of age, BMI or mobility in the historical NHANES model.</p>
      </div>
      <div className="v37-output">
        <h4>02 / The invented classifier calculates</h4>
        <div className="v37-output-number" aria-live="polite"><span>{score.toFixed(1)}%</span><small>simulated class-1 probability</small></div>
        <div className="v37-output-track" role="meter" aria-label="Simulated fictional class-1 probability" aria-valuemin={0} aria-valuemax={100} aria-valuenow={score}><span style={{width:`${score}%`}}/></div>
        <p>Class 1 is an <strong>invented teaching label</strong>, not death, disease, frailty, or a future health outcome. This value is not a medical probability.</p>
        <div className="v37-formula">logit = {BASE.toFixed(2)} {data.factors.map(f=><span key={f.name}>{safeFixed(f.contribution)}</span>)} = <b>{data.logit.toFixed(3)}</b></div>
        <div className="v37-formula-small">Output = 1 / (1 + exp(−logit))</div>
      </div>
    </div>
    <div className="v37-effects"><div className="v37-effects-head"><h4>03 / Why the fictional number changed</h4><span>Exact contributions from this illustrative formula—not SHAP or learned NHANES effects</span></div>
      {data.factors.map(f=><div className="v37-effect" key={f.name}><div><strong>{f.name}</strong><small>{f.explanation}</small></div><div className="v37-effect-axis" aria-label={`${f.name} logit contribution ${f.contribution.toFixed(3)}`}><i className="v37-zero"/><span className={f.contribution>=0?'v37-positive':'v37-negative'} style={{width:`${Math.abs(f.contribution)/1.6*48}%`,left:f.contribution>=0?'50%':`${50-Math.abs(f.contribution)/1.6*48}%`}}/></div><b>{safeFixed(f.contribution)}</b></div>)}
    </div>
    <div className="v37-boundary"><ShieldAlert size={18} aria-hidden="true"/><span><strong>Real patient inference unavailable.</strong> No historical fitted model was loaded or queried; no person's assessment was used in this simulator. A clinical output requires verified preprocessing, source mapping, governance approval, independent validation, calibration and secure serving.</span></div>
    <p className="v37-lab-footer"><CheckCircle2 size={16} aria-hidden="true"/> Software demonstration: real arithmetic, entirely invented parameters and outcome. Does not produce a patient prognosis.</p>
  </section>;
}
