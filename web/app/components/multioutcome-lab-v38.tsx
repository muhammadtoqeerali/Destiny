'use client';

import {useMemo,useState} from 'react';
import {Activity,ArrowRight,CheckCircle2,Info,LockKeyhole,RotateCcw,ShieldAlert,SlidersHorizontal} from 'lucide-react';
import registry from '../data/fictional-model-registry-v38.json';

type SignalKey='age_signal'|'bmi_signal'|'phq_signal'|'movement_signal'|'history_signal'|'smoking_signal';
type Calculation={id:string;title:string;percent:number;intercept:number;logit:number;
  effects:{key:SignalKey;name:string;normalized:number;weight:number;contribution:number}[]};
const featureNames:Record<SignalKey,string>={
  age_signal:'Invented age signal',bmi_signal:'Invented BMI signal',phq_signal:'Invented symptom signal',
  movement_signal:'Invented mobility signal',history_signal:'Invented history signal',smoking_signal:'Invented smoking signal'
};
const featureKeys=Object.keys(featureNames) as SignalKey[];
const sigmoid=(x:number)=>1/(1+Math.exp(-x));
const initial=()=>({age:75,bmi:26,phq:8,movement:0,history:0,smoking:0});
const signed=(n:number)=>`${n>=0?'+':''}${n.toFixed(3)}`;

/** Only the static synthetic fixture is scored. No Patient Assessment profile is accepted. */
export function FictionalMultiOutcomeLabV38(){
  const [sample,setSample]=useState(initial);
  const [selection,setSelection]=useState('fictional_pathway_a');
  const signals=useMemo<Record<SignalKey,number>>(()=>({
    age_signal:(sample.age-75)/10,bmi_signal:(sample.bmi-26)/8,
    phq_signal:(sample.phq-8)/8,movement_signal:sample.movement/2,
    history_signal:sample.history,smoking_signal:sample.smoking
  }),[sample]);
  const results=useMemo<Calculation[]>(()=>registry.models.map(model=>{
    const effects=featureKeys.map(key=>({key,name:featureNames[key],normalized:signals[key],
      weight:model.weights[key],contribution:signals[key]*model.weights[key]}));
    const logit=model.intercept+effects.reduce((sum,item)=>sum+item.contribution,0);
    return {id:model.id,title:model.title,percent:sigmoid(logit)*100,intercept:model.intercept,logit,effects};
  }),[signals]);
  const chosen=results.find(x=>x.id===selection)||results[0];
  const setValue=(key:keyof ReturnType<typeof initial>,value:number)=>setSample(x=>({...x,[key]:value}));
  const maxEffect=Math.max(0.5,...chosen.effects.map(x=>Math.abs(x.contribution)));
  return <section className="v38-lab" aria-label="Trained fictional multi-outcome modeling studio">
    <div className="v38-lead"><div><span className="v38-kicker"><Activity size={16}/> SYNTHETIC INFERENCE · TRAINED ON GENERATED DATA</span>
      <h3>Three outputs, one fictional scenario</h3>
      <p>Explore an <strong>actual fitted logistic model</strong> trained entirely on deterministic invented records. Change the fictional example and inspect the exact model coefficients. Outcomes A, B and C do not represent any real disease, mortality event or clinical prognosis.</p></div>
      <div className="v38-stamp"><ShieldAlert size={19}/> NOT PATIENT PREDICTIONS</div>
    </div>
    <div className="v38-layout">
      <div className="v38-controls"><h4><SlidersHorizontal size={17}/> 01 · Fictional scenario</h4>
        <label htmlFor="v38-age">Fictional age <output>{sample.age}</output></label>
        <input id="v38-age" aria-label="Synthetic age slider" type="range" min="65" max="95" step="1" value={sample.age} onChange={e=>setValue('age',Number(e.target.value))}/>
        <label htmlFor="v38-bmi">Fictional BMI <output>{sample.bmi.toFixed(1)}</output></label>
        <input id="v38-bmi" aria-label="Synthetic BMI slider" type="range" min="18" max="40" step="0.5" value={sample.bmi} onChange={e=>setValue('bmi',Number(e.target.value))}/>
        <label htmlFor="v38-phq">Fictional symptom score <output>{sample.phq}</output></label>
        <input id="v38-phq" aria-label="Synthetic symptom slider" type="range" min="0" max="27" value={sample.phq} onChange={e=>setValue('phq',Number(e.target.value))}/>
        <label htmlFor="v38-movement">Fictional movement category</label>
        <select id="v38-movement" aria-label="Synthetic movement category" value={sample.movement} onChange={e=>setValue('movement',Number(e.target.value))}>
          <option value={0}>Scenario A</option><option value={1}>Scenario B</option><option value={2}>Scenario C</option>
        </select>
        <label htmlFor="v38-history">Invented history signal</label>
        <select id="v38-history" aria-label="Synthetic history signal" value={sample.history} onChange={e=>setValue('history',Number(e.target.value))}>
          <option value={0}>Absent in scenario</option><option value={1}>Present in scenario</option>
        </select>
        <label htmlFor="v38-smoking">Invented smoking signal</label>
        <select id="v38-smoking" aria-label="Synthetic smoking signal" value={sample.smoking} onChange={e=>setValue('smoking',Number(e.target.value))}>
          <option value={0}>Absent in scenario</option><option value={1}>Present in scenario</option>
        </select>
        <button type="button" className="v38-reset" onClick={()=>setSample(initial())}><RotateCcw size={16}/> Reset fictional example</button>
        <p className="v38-small"><LockKeyhole size={16}/> This laboratory starts with an independent fictional case and never receives Patient Assessment state.</p>
      </div>
      <div className="v38-outcomes"><h4>02 · Three simultaneous illustrative outputs</h4>
        <div className="v38-result-grid">{results.map(result=><button key={result.id} type="button" className={chosen.id===result.id?'v38-result selected':'v38-result'} aria-pressed={chosen.id===result.id} onClick={()=>setSelection(result.id)}>
          <span>{result.title}</span><strong>{result.percent.toFixed(1)}%</strong><div className="v38-meter" aria-hidden="true"><i style={{width:`${result.percent}%`}}/></div><small>Fictional class-1 output · select to explain</small>
        </button>)}</div>
        <div className="v38-explanation" aria-live="polite">
          <div className="v38-explain-head"><h4>03 · Exact coefficients: {chosen.title}</h4><span>Log-odds contributions</span></div>
          <div className="v38-baseline"><span>Learned intercept on invented rows</span><b>{signed(chosen.intercept)}</b></div>
          {chosen.effects.map(e=><div className="v38-effect" key={e.key}>
            <div className="v38-effect-label"><b>{e.name}</b><small>{e.normalized.toFixed(3)} × {e.weight.toFixed(3)}</small></div>
            <div className="v38-effect-track" aria-label={`${e.name}: log-odds contribution ${signed(e.contribution)}`}>
              <i className="v38-center"/><span className={e.contribution>=0?'up':'down'} style={{left:e.contribution>=0?'50%':`${50-49*Math.abs(e.contribution)/maxEffect}%`,width:`${49*Math.abs(e.contribution)/maxEffect}%`}}/>
            </div><strong>{signed(e.contribution)}</strong>
          </div>)}
          <div className="v38-equation"><span>Sum of log-odds</span><b>{chosen.logit.toFixed(3)}</b><ArrowRight size={18}/><span>sigmoid</span><b>{chosen.percent.toFixed(1)}%</b></div>
          <p><Info size={16}/> These are exact additive contributions for a <strong>fictional fitted formula</strong>, not SHAP values from NHANES or causal effects. A simulated probability is not calibrated clinical risk.</p>
        </div>
      </div>
    </div>
    <footer className="v38-lab-foot"><CheckCircle2 size={17}/><span>Reproducible artificial training · 960 generated fit records · 240 generated holdback records · no real participant data · no network submission</span></footer>
  </section>;
}

const clinicalEndpoints=[
  {name:'Five-year all-cause mortality',status:'Historical research case blocked; no approved scoring artifact'},
  {name:'New diabetes diagnosis',status:'No trained, validated outcome-specific model'},
  {name:'Future stroke',status:'No trained, validated outcome-specific model'},
  {name:'Future heart failure',status:'No trained, validated outcome-specific model'},
];
/** Documents real clinical inference availability without accepting profile fields or displaying invented risk. */
export function ClinicalOutcomeRegistryV38(){
  return <section className="v38-readiness" aria-label="Clinical outcome availability">
    <div><span className="v38-kicker"><ShieldAlert size={16}/> REAL-MODEL RELEASE GATE</span>
      <h3>Requested future outcomes: not yet validated for individuals</h3><p>Each prediction requires its own approved training endpoint, population, preprocessing, external evaluation and registered model. Existing aggregate NHANES results do not supply new-onset disease models.</p></div>
    <div className="v38-readiness-grid">{clinicalEndpoints.map(e=><div key={e.name}><strong>{e.name}</strong><span>UNAVAILABLE</span><p>{e.status}</p></div>)}</div>
    <p className="v38-small"><LockKeyhole size={16}/> Entered assessment values never travel to this model registry. A disabled server endpoint also rejects all individual inference requests.</p>
  </section>;
}
