'use client';
import {useEffect,useState} from 'react';
import {ArrowRight,CheckCircle2,Server,ShieldAlert} from 'lucide-react';

type Contribution={feature:string;signal:number;coefficient:number;log_odds_contribution:number};
type Result={model_id:string;outcome_label:string;intercept:number;logit:number;
  synthetic_class_1_probability:number;contributions:Contribution[]};
type Reply={schema:string;mode:string;clinical_inference:boolean;patient_data_accepted:boolean;
  fixture_id:string;source_registry:string;results:Result[];disclaimer:string};
const fixtures=[
  ['fictional_reference','Reference fictional fixture'],
  ['fictional_variant_b','Invented scenario B'],
  ['fictional_variant_c','Invented scenario C']
] as const;
const signed=(x:number)=>(x>=0?'+':'')+x.toFixed(3);
/** No Patient Assessment prop. Only fixed fixture ids leave the browser via a public GET request. */
export function SyntheticServerV40(){
  const [fixture,setFixture]=useState('fictional_reference');
  const [data,setData]=useState<Reply|null>(null);
  const [error,setError]=useState('');
  const [chosen,setChosen]=useState('fictional_pathway_a');
  useEffect(()=>{
    const abort=new AbortController();
    // The value is chosen exclusively from the fixed list; no user-entered values are transmitted.
    if(!fixtures.some(f=>f[0]===fixture))return;
    fetch('/api/inference/synthetic?fixture='+fixture,{cache:'no-store',signal:abort.signal})
      .then(async r=>{if(!r.ok)throw new Error('Synthetic service unavailable');return r.json();})
      .then((x:Reply)=>{
        if(x.schema!=='FRAILTYSCOPE_SYNTHETIC_SERVING_V40'||x.fixture_id!==fixture||
           x.clinical_inference!==false||x.patient_data_accepted!==false||x.results?.length!==3){
          throw new Error('Untrusted synthetic service response');
        }
        setData(x);setError('');
      })
      .catch(e=>{if(!abort.signal.aborted){setData(null);setError(String(e.message||e));}});
    return ()=>abort.abort();
  },[fixture]);
  const selected=data?.results.find(x=>x.model_id===chosen)||data?.results[0];
  return <section className="v40-synthetic" aria-label="Synthetic server-side inference">
    <div className="v40-head"><div><span className="v40-eyebrow"><Server size={16} aria-hidden="true"/> LIVE SOFTWARE PIPELINE / FICTIONAL ONLY</span>
      <h3>A working server-side model and explanation</h3>
      <p>This calls a real Next.js inference route using one of three <strong>predefined invented scenarios</strong>. It runs the three previously fitted fictional classifiers and returns exact additive contributions. It never accepts a Patient Assessment profile.</p></div>
      <span className="v40-warning"><ShieldAlert size={16} aria-hidden="true"/> NOT FOR CLINICAL USE</span>
    </div>
    <div className="v40-selector"><label htmlFor="v40-fixture">Choose a fictional fixture</label><select id="v40-fixture" value={fixture} onChange={e=>{setData(null);setFixture(e.target.value);}}>{fixtures.map(f=><option key={f[0]} value={f[0]}>{f[1]}</option>)}</select></div>
    {error&&<p className="v40-error" role="alert">{error}</p>}
    {!data&&!error&&<p role="status" className="v40-loading">Calculating fictional outputs on server…</p>}
    {data&&<>
      <div className="v40-results">{data.results.map(x=><button type="button" className={selected?.model_id===x.model_id?'selected':''} key={x.model_id} aria-pressed={selected?.model_id===x.model_id} onClick={()=>setChosen(x.model_id)}><small>{x.outcome_label}</small><strong>{(100*x.synthetic_class_1_probability).toFixed(1)}%</strong><span>Fictional class-1 output only</span></button>)}</div>
      {selected&&<div className="v40-explainer"><h4>Exactly why {selected.outcome_label} changed</h4><div className="v40-line"><span>Learned fictional intercept</span><b>{signed(selected.intercept)}</b></div>
        {selected.contributions.map(c=><div className="v40-line" key={c.feature}><span>{c.feature.replaceAll('_',' ')} <small>{c.signal.toFixed(3)} × {c.coefficient.toFixed(3)}</small></span><b>{signed(c.log_odds_contribution)}</b></div>)}
        <div className="v40-total"><span>Sum of log-odds <ArrowRight size={14} aria-hidden="true"/> sigmoid</span><b>{selected.logit.toFixed(3)} → {(100*selected.synthetic_class_1_probability).toFixed(1)}%</b></div>
      </div>}
      <p className="v40-proof"><CheckCircle2 size={16} aria-hidden="true"/> Server response: {data.schema} · Registry {data.source_registry} · GET-only fixture contract</p>
    </>}
    <p className="v40-boundary"><ShieldAlert size={17} aria-hidden="true"/> Invention-only outputs A, B and C. These percentages do not represent death, diabetes, stroke, heart failure or any future illness. Real patient inference remains forbidden by the NHANES governance contract.</p>
  </section>;
}
