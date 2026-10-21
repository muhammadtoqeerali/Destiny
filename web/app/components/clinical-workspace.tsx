'use client';
import { useMemo, useState } from 'react';
import { Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Brain, ChevronLeft, ChevronRight, ClipboardList, HeartPulse, Info, Search, ShieldAlert, Stethoscope, Users, UserRound } from 'lucide-react';
import demo from '../../public/data/demo.json';

type Case = (typeof demo.patients)[number];
type Filter = 'All cases' | 'Lower' | 'Moderate' | 'Higher';
type View = 'Overview' | 'Measurements' | 'Score explanation';
const FEATURE_SECTIONS:[string,string[],string][]=[
 ['Movement & physical function',['gait_speed_ms','sppb_score','grip_strength_kg','activity_minutes_day'],'Movement and strength may be related to overall functional health.'],
 ['Cognition & nutrition',['moca_score','bmi','weight_loss','oral_health_problem'],"These measurements describe distinct parts of a person’s overall health."],
 ['Health history & background',['previous_fall','medication_count','comorbidity_count','exhaustion','age','sex'],'Recorded characteristics and background information in this simulated case.']
];
const allCases=demo.patients;
const PAGE_SIZE=6;
function CaseStatus({band}:{band:string}){return <span className={'case-band case-'+band.toLowerCase()}>{band} model band</span>}
function Metric({label,value,detail}:{label:string,value:string,detail:string}){return <div className="doctor-metric"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>}
function Heading({kicker,title,detail}:{kicker:string,title:string,detail?:string}){return <div className="doctor-section-heading"><span className="micro-label">{kicker}</span><h2>{title}</h2>{detail&&<p>{detail}</p>}</div>}
export function ClinicalWorkspace(){
 const [search,setSearch]=useState('');
 const [filter,setFilter]=useState<Filter>('All cases');
 const [selectedId,setSelectedId]=useState(allCases[0].id);
 const [view,setView]=useState<View>('Overview');
 const [page,setPage]=useState(0);
 const selected=allCases.find(c=>c.id===selectedId) || allCases[0];
 const results=useMemo(()=>allCases.filter(c=>(filter==='All cases'||c.band===filter) && `${c.id} ${c.age} ${c.sex}`.toLowerCase().includes(search.toLowerCase())),[filter,search]);
 const maxPage=Math.max(0,Math.ceil(results.length/PAGE_SIZE)-1);
 const visible=results.slice(Math.min(page,maxPage)*PAGE_SIZE,(Math.min(page,maxPage)+1)*PAGE_SIZE);
 const missing=selected.features.filter(f=>f.is_missing).length;
 const feature=(key:string)=>selected.features.find(f=>f.key===key);
 const selectCase=(id:string)=>{setSelectedId(id);setView('Overview')};
 const filterChange=(value:Filter)=>{setFilter(value);setPage(0)};
 return <div className="doctor-view">
  <div className="doctor-hero"><div><span className="hero-eyebrow"><span className="hero-pulse"/> CLINICAL WORKSPACE / SYNTHETIC CASES</span><h1>Care begins with <em>clarity.</em></h1><p>Understand a fictional older person's health profile, see important measurements and explore how an experimental model responds to them.</p></div><div className="hero-icon"><Stethoscope size={48}/></div></div>
  <div className="doctor-safety" role="note"><ShieldAlert size={22}/><div><strong>Training and demonstration only</strong><span>All records and outcomes are invented. Scores are not real-world predictions, diagnoses, risk thresholds or treatment recommendations.</span></div></div>
  <div className="doctor-summary"><Metric label="Fictional cases" value={String(allCases.length)} detail="Sampled artificial test records"/><Metric label="Current case age" value={`${selected.age} years`} detail="Simulated patient age"/><Metric label="Recorded variables" value={String(selected.features.length)} detail={`${missing} missing in this example`}/></div>
  <section className="case-browser"><div className="case-browser-title"><div><span className="micro-label">PATIENT DIRECTORY</span><h2>Choose a simulated patient</h2><p>Search, filter and open a case without navigating away.</p></div><div className="case-search-controls"><label className="case-search"><Search size={18}/><input aria-label="Search fictional patients" placeholder="Search ID, age, sex..." value={search} onChange={e=>{setSearch(e.target.value);setPage(0)}}/></label><select aria-label="Filter model band" value={filter} onChange={e=>filterChange(e.target.value as Filter)}>{(['All cases','Lower','Moderate','Higher'] as Filter[]).map(f=><option key={f}>{f}</option>)}</select></div></div>
   <div className="case-cards">{visible.length?visible.map(c=><button className={'case-choice '+(c.id===selected.id?'case-selected':'')} key={c.id} onClick={()=>selectCase(c.id)} aria-pressed={c.id===selected.id}><div className="case-choice-top"><span className="case-avatar"><UserRound size={18}/></span>{c.id===selected.id&&<span className="case-selected-dot"/>}</div><strong>{c.id}</strong><span>{c.age} years · {c.sex}</span><CaseStatus band={c.band}/></button>):<p className="no-cases">No matching simulated cases found.</p>}</div>
   <div className="case-browser-footer"><span>{results.length===0?'No cases':`${Math.min(page,maxPage)*PAGE_SIZE+1}–${Math.min((Math.min(page,maxPage)+1)*PAGE_SIZE,results.length)} of ${results.length}`} cases</span><div><button aria-label="Previous patient page" disabled={page<=0} onClick={()=>setPage(v=>Math.max(0,v-1))}><ChevronLeft size={17}/></button><button aria-label="Next patient page" disabled={page>=maxPage} onClick={()=>setPage(v=>Math.min(maxPage,v+1))}><ChevronRight size={17}/></button></div></div>
  </section>
  <div className="case-detail-head"><div><span className="micro-label">SELECTED PATIENT / SYNTHETIC</span><h2>{selected.id} <CaseStatus band={selected.band}/></h2><p>{selected.age} years · {selected.sex} · no personal or identifiable patient information</p></div><span className="case-detail-code"><ClipboardList size={17}/> Case review</span></div>
  <div className="case-tabs" role="tablist" aria-label="Patient case details">{(['Overview','Measurements','Score explanation'] as View[]).map(t=><button key={t} role="tab" aria-selected={view===t} className={view===t?'active':''} onClick={()=>setView(t)}>{t}</button>)}</div>
  {view==='Overview'&&<><div className="doctor-detail-grid"><section className="doctor-card score-card"><div className="doctor-card-title"><span className="micro-label">EXPERIMENTAL MODEL OUTPUT</span><h3>Illustrative event score</h3><p>Made-up 12-month fall-event outcome</p></div><div className="score-display"><div className="score-ring" style={{background:`conic-gradient(#187c75 ${selected.risk}%, #e5efec ${selected.risk}% 100%)`}}><span><strong>{selected.risk.toFixed(1)}%</strong><small>model score</small></span></div><div><CaseStatus band={selected.band}/><h4>How to read this value</h4><p>The model places this fictional case at this score within a simulated dataset. It cannot determine whether this or any real person will fall.</p></div></div><div className="explain-note"><Info size={18}/> The display bands are illustrative grouping labels, not validated clinical cutoffs.</div></section>
      <section className="doctor-card"><div className="doctor-card-title"><span className="micro-label">QUICK HEALTH SNAPSHOT</span><h3>Measurements at a glance</h3><p>A few example values from this fictional case</p></div><div className="quick-measures">{['gait_speed_ms','sppb_score','grip_strength_kg','moca_score'].map(k=>{const f=feature(k);return <div key={k}><span>{f?.name||k}</span><strong>{f?.value||'Not available'}</strong>{f?.is_missing&&<small>Not measured</small>}</div>})}</div><button className="inline-action" onClick={()=>setView('Measurements')}>View all 14 measurements <ArrowRight size={17}/></button></section></div>
      <section className="doctor-card overview-guide"><div><div className="guide-symbol"><HeartPulse size={22}/></div><h3>A simple reading workflow</h3><p>Look at the observed measurements first, check which are missing, then examine how a single input changes the example's model score. None of these steps replaces professional assessment.</p></div><button className="secondary-action" onClick={()=>setView('Score explanation')}>Understand the model output <ArrowRight size={16}/></button></section>
    </>}
  {view==='Measurements'&&<><Heading kicker="HEALTH PROFILE" title="The complete fictional record" detail="All 14 inputs used by the expanded demonstration model, arranged by clinical domain."/>
   {FEATURE_SECTIONS.map(([name,keys,detail])=><section className="doctor-card feature-section" key={name}><div className="doctor-card-title"><h3>{name}</h3><p>{detail}</p></div><div className="all-features">{keys.map(k=>{const f=feature(k);return <div key={k}><span>{f?.name||k}</span><strong>{f?.value||'Not available'}</strong>{f?.is_missing&&<small className="missing-pill">Missing / not recorded</small>}</div>})}</div></section>)}
   <div className="explain-note"><Info size={18}/> Values were generated for research software testing and do not represent patients or HUNT observations.</div>
  </>}
  {view==='Score explanation'&&<><Heading kicker="TRANSPARENT MODELING" title="Why did the demonstration score change?" detail="The largest one-feature comparisons for this fictional patient, translated into plain language."/>
    <section className="doctor-card"><div className="doctor-card-title"><h3>Five strongest example-level responses</h3><p>The difference in predicted percentage points when one measurement is replaced by a typical synthetic reference.</p></div><div className="doctor-explanation-list">{selected.explanations.map((f,i)=><div className="doctor-explanation" key={f.key}><div className="explanation-index">{String(i+1).padStart(2,'0')}</div><div className="explanation-description"><strong>{f.name}</strong><span>Recorded: {f.value}</span><div className="explanation-track"><i className={f.delta_pp>=0?'positive':'negative'} style={{width:`${Math.min(Math.abs(f.delta_pp)/25*100,100)}%`}}/></div></div><span className={'explanation-value '+(f.delta_pp>=0?'positive':'negative')}>{f.delta_pp>=0?<ArrowUpRight size={17}/>:<ArrowDownRight size={17}/>} {f.delta_pp>0?'+':''}{f.delta_pp.toFixed(1)} pp</span></div>)}</div></section>
    <section className="doctor-card plain-language"><div className="guide-symbol"><Brain size={22}/></div><div><h3>What this explanation means</h3><p>A positive difference means the experiment's probability estimate increases when the fictional case uses its recorded value instead of a synthetic reference. A negative difference means the estimate decreases. These comparisons are <strong>not causal</strong>, do not add up to the total score, and are not treatment recommendations or SHAP attributions.</p></div></section>
   </>}
  <div className="doctor-bottom-note"><Users size={16}/> 90 fictional cases displayed from a larger synthetic research cohort · No clinical decision-making</div>
 </div>;
}
