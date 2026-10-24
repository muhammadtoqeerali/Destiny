'use client';
import {useState} from 'react';
import Link from 'next/link';
import {Activity, ArrowRight, BarChart3, BrainCircuit, Database, LockKeyhole, ShieldCheck, Users} from 'lucide-react';
import demo from '../data/interview-benchmark-v47.json';
import historical from '../../public/data/nhanes-refinement.json';

type Example=(typeof demo.fictional_examples)[number];
const percent=(x:number)=>(100*x).toFixed(1)+'%';
const show=(x:number|null,unit:string)=>x===null?'Not recorded':String(x)+unit;

export function InterviewDoctorV47(){
 const [chosen,setChosen]=useState(0);
 const [more,setMore]=useState(false);
 const selected:Example=demo.fictional_examples[chosen];
 return <main className="if-page" aria-label="Interview-focused doctor overview">
  <div className="if-breadcrumb">FRAILTYSCOPE / CLINICIAN VIEW / FICTIONAL EXAMPLES</div>
  <header className="if-banner"><div><span className="if-eyebrow"><Activity size={16}/> RESEARCH DEMONSTRATOR</span>
    <h1>Older adult health, made understandable.</h1>
    <p>Explore a small set of deliberately fictional ageing profiles and see how a reproducible machine-learning model summarizes future functional decline. No data entry or patient registration.</p>
    <div className="if-actions"><Link href="/admin/interview">Explore ML evidence <ArrowRight size={16}/></Link><Link href="/doctor">Open existing research workspace</Link></div>
  </div><aside className="if-banner-note"><b>Important distinction</b><span>All individual profiles and their probabilities on this page are generated. They are not patients or HUNT participants. The historical NHANES results are maintained separately.</span></aside></header>
  <div className="if-mini-stats"><div><span>Generated cohort</span><b>{demo.configuration.generation_n.toLocaleString()}</b><small>Invented older-adult examples</small></div><div><span>Profiles shown</span><b>{demo.fictional_examples.length}</b><small>No identifiable records</small></div><div><span>Illustrated outcome</span><b>ADL decline</b><small>Fictional next-period status</small></div></div>
  <div className="if-doctor-grid"><section className="if-card if-people" aria-label="Fictional profile selection"><div className="if-section-head"><div><span className="if-caption">PROFILE EXPLORER</span><h2>Older-adult examples</h2><p>Choose an invented profile. Each example is separate from real survey records.</p></div></div>
    <div className="if-people-scroll">{demo.fictional_examples.map((person,i)=><button key={person.id} onClick={()=>setChosen(i)} type="button" aria-pressed={chosen===i} className={'if-person'+(chosen===i?' is-selected':'')}>
        <span className="if-avatar">{String(i+1).padStart(2,'0')}</span><span className="if-person-body"><strong>Example {i+1}</strong><small>{person.age} years · {person.sex} · {person.current_conditions.length} documented conditions</small></span><ArrowRight size={15}/>
      </button>)}</div></section>
    <div className="if-main-details"><section className="if-card"><div className="if-section-head"><div><span className="if-caption">ILLUSTRATIVE RECORD</span><h2>Health snapshot · Example {chosen+1}</h2><p>{selected.age} years, {selected.sex} · {selected.id}</p></div><span className="if-tag">Generated</span></div>
        <div className="if-person-metrics"><div><small>Current ADL limitations</small><b>{selected.adl_limitations}</b></div><div><small>Gait speed</small><b>{show(selected.gait_speed_mps,' m/s')}</b></div><div><small>Grip strength</small><b>{show(selected.grip_strength_kg,' kg')}</b></div></div>
        <h3 className="if-subhead">Current reported conditions</h3><div className="if-conditions">{selected.current_conditions.length?selected.current_conditions.map(c=><span key={c}>{c}</span>):<span>No conditions included in this fictional profile</span>}</div>
      </section>
      <section className="if-card"><div className="if-section-head"><div><span className="if-caption">MODEL EXPLANATION · FICTIONAL</span><h2>How the pipeline describes future function</h2></div><span className="if-tag">Not clinical</span></div>
        <div className="if-risk"><strong>{percent(selected.fictional_model_probability)}</strong><span>Predicted probability of invented follow-up ADL decline</span></div>
        <div className="if-meter" aria-label={'Fictional probability '+percent(selected.fictional_model_probability)}><i style={{width:percent(selected.fictional_model_probability)}}/></div>
        {selected.illustrative_factors.length>0&&<div className="if-contribution"><h3 className="if-subhead">What moves this fictional model score?</h3><p className="if-muted">Exact transformed-input contributions to log-odds for the selected logistic model; not medical causes or a validated explanation.</p><div className="if-factor-list">{selected.illustrative_factors.map(f=><div key={f.feature}><span>{f.feature.replaceAll('_',' ')}</span><strong>{f.log_odds_contribution>=0?'+':''}{f.log_odds_contribution.toFixed(2)} <small>{f.log_odds_contribution>=0?'raises':'lowers'} model score</small></strong></div>)}</div></div>}
        <p className="if-muted">This is a score computed by a model trained on artificial labels. The number cannot be interpreted as an actual patient's risk. The observable fictional follow-up label for this example is {selected.observed_demo_outcome===1?'decline':'no decline'}.</p>
        <button className="if-textlink" type="button" aria-expanded={more} onClick={()=>setMore(x=>!x)}>{more?'Hide':'Show'} the model pipeline explanation <ArrowRight size={15}/></button>
        {more&&<div className="if-steps"><span>Baseline measurements</span><ArrowRight size={14}/><span>Train-only imputation and encoding</span><ArrowRight size={14}/><span>Model probability</span><ArrowRight size={14}/><span>Synthetic evaluation</span><p>For a genuinely meaningful feature-level explanation, we will use model-specific attribution with stability checks after selecting and validating the real-data model. This panel does not invent causal explanations.</p></div>}
      </section></div>
  </div>
  <p className="if-endnote"><ShieldCheck size={16}/> Public interview view: synthetic people only. The legacy Doctor workspace is available through the link above, with technical demonstrations separated from this primary story.</p>
 </main>;
}

type Cohort='synthetic'|'nhanes'|'nhats'|'share'|'hunt';
const datasets:[Cohort,string,string][]=[['synthetic','Artificial ageing cohort','Generated demo'],['nhanes','NHANES 2011–2014','Historical research'],['nhats','NHATS','Not downloaded'],['share','SHARE','Registration needed'],['hunt','HUNT4 70+','Restricted access']];
export function InterviewAdminV47(){
 const [dataset,setDataset]=useState<Cohort>('synthetic');
 const selected=datasets.find(d=>d[0]===dataset)!;
 return <main className="if-page" aria-label="Interview-focused research admin overview">
  <div className="if-breadcrumb">FRAILTYSCOPE / ML RESEARCH / DATASET-SPECIFIC EXPERIMENTS</div>
  <header className="if-banner if-admin-banner"><div><span className="if-eyebrow"><BrainCircuit size={16}/> MACHINE LEARNING RESEARCH</span><h1>From raw variables to model evidence.</h1>
    <p>Select one dataset to see its actual status, preprocessing choices, candidate models and evaluation. Different outcomes and cohorts are never pooled or ranked as if they were the same task.</p>
    <div className="if-actions"><Link href="/interview">View clinician presentation <ArrowRight size={16}/></Link><Link href="/admin">Open full technical research studio</Link></div>
  </div><aside className="if-banner-note"><b>Experiment identity first</b><span>Model rankings are valid only within the same dataset, outcome definition and validation protocol. No model is declared universally best.</span></aside></header>
  <section className="if-card if-datasets"><div className="if-section-head"><div><span className="if-caption">01 · DATASET SELECTION</span><h2>Choose a research dataset</h2></div></div>
    <div className="if-dataset-tabs" role="group" aria-label="Select dataset">{datasets.map(d=><button key={d[0]} type="button" aria-pressed={dataset===d[0]} className={dataset===d[0]?'is-selected':''} onClick={()=>setDataset(d[0])}><b>{d[1]}</b><small>{d[2]}</small></button>)}</div>
    <p className="if-muted">Selected: <strong>{selected[1]}</strong> · {selected[2]}. Source-specific results only.</p>
  </section>
  {dataset==='synthetic'&&<><section className="if-card"><div className="if-section-head"><div><span className="if-caption">02 · DATA / TARGET / PREPROCESSING</span><h2>Generated functional-decline benchmark</h2><p>All 1,800 records and future labels are invented; this measures pipeline correctness, not HUNT performance.</p></div><span className="if-tag">Synthetic-only</span></div>
      <div className="if-mini-stats if-inner-stats"><div><span>Train</span><b>{demo.configuration.train_n}</b><small>Distinct fictional people</small></div><div><span>Validation</span><b>{demo.configuration.validation_n}</b><small>Model selection</small></div><div><span>Final test</span><b>{demo.configuration.test_n}</b><small>Used once</small></div></div>
      <div className="if-method"><div><b>Inputs</b><span>{demo.configuration.features.join(', ')}</span></div><div><b>Preprocessing</b><span>Training-fold-only median/mode imputation, missing indicators, numeric scaling, categorical one-hot encoding</span></div><div><b>Target</b><span>{demo.target}. No real follow-up observations.</span></div><div><b>Selection</b><span>{demo.configuration.selection}</span></div></div>
    </section><section className="if-card"><div className="if-section-head"><div><span className="if-caption">03 · CANDIDATES / METRICS</span><h2>Transparent model comparison</h2><p>Same generated split, same features and selection metric. These validation numbers are not state-of-the-art benchmarks.</p></div></div>
      <div className="if-table-wrap"><table><thead><tr><th>Model</th><th>Validation ROC-AUC ↑</th><th>Average precision ↑</th><th>Brier ↓</th><th>Decision</th></tr></thead><tbody>{demo.models.map(model=><tr key={model.name}><td><strong>{model.name}</strong></td><td>{model.validation.roc_auc.toFixed(3)}</td><td>{model.validation.average_precision.toFixed(3)}</td><td>{model.validation.brier.toFixed(3)}</td><td>{model.name===demo.selected_model?'Selected on validation':'Compared'}</td></tr>)}</tbody></table></div>
      <div className="if-metricline"><div><small>Validation-selected algorithm</small><b>{demo.selected_model}</b></div><div><small>Held-aside synthetic test ROC-AUC</small><b>{demo.synthetic_test.roc_auc.toFixed(3)}</b></div><div><small>Held-aside synthetic test Brier</small><b>{demo.synthetic_test.brier.toFixed(3)}</b></div></div>
      <h3 className="if-subhead">Calibration by synthetic prediction band</h3><div className="if-table-wrap"><table><thead><tr><th>Score band</th><th>Number</th><th>Mean predicted</th><th>Observed fictional fraction</th></tr></thead><tbody>{demo.calibration.map(x=><tr key={x.band}><td>{x.band}</td><td>{x.count}{x.count<20?' · sparse':''}</td><td>{percent(x.mean_probability)}</td><td>{percent(x.observed_fraction)}</td></tr>)}</tbody></table></div>
      <p className="if-muted">Small calibration bins are unstable; there is no external validation, clinical interpretation or real-world generalization from this synthetic experiment.</p>
   </section></>}
  {dataset==='nhanes'&&<section className="if-card"><div className="if-section-head"><div><span className="if-caption">HISTORICAL NHANES RESEARCH · SEPARATE TASK</span><h2>Approximately five-year all-cause mortality</h2><p>Pre-existing published aggregates from NHANES 2011–2014. The later cycle was previously inspected, so this is not independent validation. No new analysis is authorized.</p></div><span className="if-tag">Historical only</span></div>
      <div className="if-mini-stats if-inner-stats"><div><span>Historical participants</span><b>{historical.counts.total.toLocaleString()}</b><small>Age 65+</small></div><div><span>Earlier development</span><b>{historical.counts.development.toLocaleString()}</b><small>2011–2012</small></div><div><span>Previously inspected</span><b>{historical.counts.test.toLocaleString()}</b><small>2013–2014</small></div></div>
      <div className="if-method"><div><b>Endpoint</b><span>Approximately five-year all-cause mortality (not incident diabetes, stroke or heart failure)</span></div><div><b>Inputs</b><span>14 historical candidate predictors; only 3 partially source-mapped in the current public harmonization contract</span></div><div><b>Governance</b><span>BLOCKED_FOR_NEW_ANALYSIS; source timing and independent validation unresolved</span></div></div>
      <h3 className="if-subhead">Historical validation-stage model comparison</h3><div className="if-table-wrap"><table><thead><tr><th>Candidate</th><th>AUC</th><th>Brier ↓</th></tr></thead><tbody>{historical.models.map(m=><tr key={m.name}><td>{m.name}</td><td>{m.auc.toFixed(3)}</td><td>{m.brier.toFixed(3)}</td></tr>)}</tbody></table></div>
      <p className="if-muted">Do not compare these figures directly with the artificial ADL-decline benchmark; datasets, targets and evaluation histories differ.</p>
   </section>}
  {(dataset==='nhats'||dataset==='share'||dataset==='hunt')&&<section className="if-card if-empty"><Database size={32}/><h2>No experiment has been run on {selected[1]} here.</h2><p>{dataset==='hunt'?'HUNT participant-level research data require project-specific authorization. We can inspect its public variable dictionary, but not assert access.':dataset==='nhats'?'NHATS public-use files require a user registration and local download under their terms. Once available, we can map waves and define prospective functional decline.':'SHARE scientific-use files require individual registration and compliance with its conditions. Once available, we can map longitudinal measurements and frailty outcomes.'}</p><strong>Required next: dataset access → variable dictionary → outcome definition → reproducible fit and evaluation.</strong></section>}
  <p className="if-endnote"><LockKeyhole size={16}/> Admin findings are dataset-specific. Real individual-level records do not appear in this public demo; the full historical research studio remains available separately.</p>
 </main>;
}
