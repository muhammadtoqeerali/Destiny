'use client';

import { useMemo, useState } from 'react';
import { Activity, BarChart3, CalendarDays, Check, ClipboardList, FileHeart, HeartPulse, Info, Plus, Search, ShieldCheck, Stethoscope, Trash2, TrendingUp, Users } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import study from '../../public/data/nhanes-aggregate.json';
import enhanced from '../../public/data/nhanes-refinement.json';
import profiles from '../../public/data/nhanes-cohort-profile.json';
import { ResearchBoundaryNotice } from './research-boundary-notice';
import { DoctorHeroV35, CohortSnapshotV35 } from './doctor-visuals-v35';
import {DoctorJourneyV36, FollowUpSummaryV36, PredictionStoryV36} from './doctor-journey-v36';
import {InferenceReadinessV37, FictionalScoringLabV37} from './inference-readiness-v37';
import {ClinicalOutcomeRegistryV38, FictionalMultiOutcomeLabV38} from './multioutcome-lab-v38';
import {ReadinessEvidenceV39} from './inference-evidence-v39';
import {SyntheticServerV40} from './synthetic-server-v40';
import {ValidationGateV41} from './validation-gate-v41';
import {ModelTranslationV42} from './model-translation-v42';
import {ArtifactAcceptanceV43} from './artifact-acceptance-v43';
import {StudyHandoffV44} from './study-handoff-v44';

type Page = 'Population overview' | 'Health profiles' | 'Patient assessment' | 'Visit history' | 'Model evidence';
type CaseValues = Record<string,string>;
type Visit = {id:number;date:string;bmi:number|null;phq:number|null};
const PAGES:Page[] = ['Population overview','Health profiles','Patient assessment','Visit history','Model evidence'];
const LABELS:Record<string,string> = {
  age:'Age (years)',sex:'Sex',bmi:'Body mass index (kg/m²)',phq9_score:'PHQ-9 total (0–27)',
  walking_difficulty:'Walking difficulty',stairs_difficulty:'Stair difficulty',stooping_difficulty:'Stooping difficulty',
  heart_failure:'Heart failure',coronary_disease:'Coronary disease',stroke:'Stroke',
  cancer:'Cancer',diabetes:'Diabetes',hypertension:'Hypertension',ever_smoked:'Smoking history'
};
const CHRONIC=['heart_failure','coronary_disease','stroke','cancer','diabetes','hypertension','ever_smoked'];
const MOBILITY=['walking_difficulty','stairs_difficulty','stooping_difficulty'];
const clinicalPct=(x:number)=>(x*100).toFixed(1)+'%';
const isValidAssessment=(key:string, raw:string)=>{
  if(raw==='')return false;
  if(key==='age'){const n=Number(raw);return Number.isInteger(n)&&n>=65&&n<=110;}
  if(key==='bmi'){const n=Number(raw);return Number.isFinite(n)&&n>=10&&n<=70;}
  if(key==='phq9_score'){const n=Number(raw);return Number.isInteger(n)&&n>=0&&n<=27;}
  return true;
};
function Header({eyebrow,title,description}:{eyebrow:string;title:string;description:string}){
 return <div className="v7-heading"><span className="nh-kicker">{eyebrow}</span><h2>{title}</h2><p>{description}</p></div>;
}
function Box({title,desc,children}:{title:string;desc?:string;children:React.ReactNode}){
 return <section className="v7-card"><div className="v7-cardhead"><h3>{title}</h3>{desc&&<p>{desc}</p>}</div>{children}</section>;
}
function Pill({children}:{children:React.ReactNode}){return <span className="v7-pill">{children}</span>}
export function ClinicalWorkspace(){
 const [page,setPage]=useState<Page>('Population overview');
 const [group,setGroup]=useState('All 65+');
 const activeGroup=profiles.groups.find(x=>x.name===group)||profiles.groups[0];
 const [profile,setProfile]=useState<CaseValues>({});
 const [visits,setVisits]=useState<Visit[]>([]);
 const [visitDate,setVisitDate]=useState('');
 const [visitBmi,setVisitBmi]=useState('');
 const [visitPhq,setVisitPhq]=useState('');
 const setField=(key:string,value:string)=>setProfile(p=>({...p,[key]:value}));
 const recorded=Object.entries(profile).filter(([key,value])=>isValidAssessment(key,value)).length;
 const invalidEntries=Object.entries(profile).filter(([key,value])=>value!==''&&!isValidAssessment(key,value));
 const present=CHRONIC.filter(k=>profile[k]==='Yes');
 const mobility=MOBILITY.filter(k=>['Some difficulty','Much difficulty','Unable to do'].includes(profile[k])).map(k=>LABELS[k]);
 const total=Object.keys(LABELS).length;
 const trend=useMemo(()=>visits.slice().sort((a,b)=>a.date.localeCompare(b.date)).map(x=>({...x,period:x.date})),[visits]);
 const addVisit=()=>{
   if(!visitDate || (!visitBmi && !visitPhq))return;
   const b=visitBmi===''?null:Number(visitBmi);
   const p=visitPhq===''?null:Number(visitPhq);
   if((b!==null&&(!Number.isFinite(b)||b<10||b>70))||(p!==null&&(!Number.isInteger(p)||p<0||p>27)))return;
   setVisits(old=>[...old.filter(x=>x.date!==visitDate),{id:Date.now(),date:visitDate,bmi:b,phq:p}]);
   setVisitBmi('');setVisitPhq('');
 };
 return <div className="v7-portal v35-doctor">
  <DoctorHeroV35 onNavigate={destination=>setPage(destination)}/>
  <nav className="v7-topnav" aria-label="Doctor workspace">{PAGES.map((t,i)=><button key={t} type="button" aria-label={t} aria-controls="v35-doctor-content" aria-current={page===t?'page':undefined} className={page===t?'active':''} onClick={()=>setPage(t)}><span className="v35-tab-number" aria-hidden="true">{String(i+1).padStart(2,'0')}</span>{t}</button>)}</nav>
  <div className="v35-scope" role="note"><ShieldCheck size={19} aria-hidden="true"/><div><b>Historical research evidence · not a clinical prediction service</b><span>Published NHANES aggregates and temporary, de-identified browser examples only.</span><details><summary>Research scope and limitations</summary><ResearchBoundaryNotice/></details></div></div>
  <div id="v35-doctor-content" className="v35-doctor-content" role="region" aria-label={page}>
  {page==='Population overview'&&<>
   <div className="v7-stats"><div><span>Study participants</span><strong>{study.counts.total.toLocaleString()}</strong><small>NHANES 2011–2014 · 65+</small></div><div><span>Later-cycle participants</span><strong>{study.counts.test.toLocaleString()}</strong><small>2013–2014 evaluation cohort</small></div><div><span>Recorded mortality events</span><strong>{study.counts.test_events}</strong><small>Approximate five-year horizon</small></div><div><span>Observed event fraction</span><strong>{clinicalPct(study.counts.test_events/study.counts.test)}</strong><small>Unweighted study subset</small></div></div>
   <CohortSnapshotV35/>
   <div className="v7-two"><Box title="Participant age distribution" desc="Counts across the combined eligible analysis sample"><div className="v7-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={enhanced.ageDistribution}><CartesianGrid stroke="#eef3f1" strokeDasharray="4 4"/><XAxis dataKey="group" tick={{fontSize:11}}/><YAxis allowDecimals={false} tick={{fontSize:11}}/><Tooltip/><Bar dataKey="count" fill="#2b8980" name="Participants" radius={[6,6,0,0]}/></BarChart></ResponsiveContainer></div><p className="v7-fine">Public NHANES ages of 80 and above are grouped together.</p></Box>
   <Box title="Health domains in the study" desc="Baseline information available to the research models"><div className="v7-domain-list">{[['Mobility','Walking, stairs and stooping difficulty'],['Physical health','BMI, diabetes, stroke, cardiovascular disease and cancer'],['Mental health','PHQ-9 depressive-symptom score'],['Demographics','Age, sex and smoking history']].map(([a,b])=><div key={a}><span className="v7-dot"/><strong>{a}</strong><p>{b}</p></div>)}</div></Box></div>
   <div className="v7-two"><Box title="Data availability" desc="Observed values before missing-data preprocessing"><div className="v7-coverage">{enhanced.featureCoverage.slice().sort((a,b)=>a.observed-b.observed).map(f=><div className="v7-cover-row" key={f.name}><span>{f.name}</span><div className="v7-cover-track"><i style={{width:f.observed+'%'}}/></div><b>{f.observed.toFixed(1)}%</b></div>)}</div></Box>
   <Box title="Clinical study endpoint" desc="All-cause mortality follow-up from public linked records"><div className="v7-summary-line"><span>Outcome</span><strong>All-cause mortality</strong></div><div className="v7-summary-line"><span>Observation horizon</span><strong>Approximately five years</strong></div><div className="v7-summary-line"><span>Model</span><strong>{enhanced.selectedModel}</strong></div><div className="v7-summary-line"><span>Historical later-cycle ROC-AUC</span><strong>{enhanced.test.roc_auc.toFixed(3)}</strong></div><div className="v7-info"><Info size={18}/> Cohort statistics describe research participants and do not establish individual prognosis.</div></Box></div>
  </>}
  {page==='Health profiles'&&<>
   <Header eyebrow="COHORT HEALTH CHARACTERISTICS" title="Health profiles" description="Observed health indicators across NHANES participant groups, using published aggregate statistics rather than individual records."/>
   <div className="v8-profile-controls"><label htmlFor="v8-group">Participant group</label><select id="v8-group" value={group} onChange={e=>setGroup(e.target.value)}>{profiles.groups.map(g=><option key={g.name} value={g.name}>{g.name} · {g.n.toLocaleString()} records</option>)}</select></div>
   <div className="v7-stats"><div><span>Records in group</span><strong>{activeGroup.n.toLocaleString()}</strong><small>Eligible linked observations</small></div><div><span>Weighted mean BMI</span><strong>{activeGroup.mean_bmi_weighted===null?'—':activeGroup.mean_bmi_weighted.toFixed(1)}</strong><small>kg/m² · observed participants</small></div><div><span>Conditions shown</span><strong>{activeGroup.conditions.length}</strong><small>Disclosure-screened indicators</small></div><div><span>Mobility indicators</span><strong>{activeGroup.mobility.length}</strong><small>Available domain comparisons</small></div></div>
   <div className="v7-two">
    <Box title="Reported health conditions" desc="Survey-weighted prevalence among participants with recorded responses">
     <div className="v8-bars">{activeGroup.conditions.length?activeGroup.conditions.map(c=><div key={c.label} className="v8-barrow"><div><b>{c.label}</b><small>{c.n_observed} recorded · {c.percent.toFixed(1)}% unweighted</small></div><div className="v8-bartrack"><span style={{width:c.weighted_percent+'%'}}/></div><strong>{c.weighted_percent.toFixed(1)}%</strong></div>):<p className="v7-empty">No indicators meet the group-level reporting threshold.</p>}</div>
    </Box>
    <Box title="Functional difficulty" desc="Reported some/much difficulty or unable to perform the activity">
     <div className="v8-bars">{activeGroup.mobility.length?activeGroup.mobility.map(m=><div key={m.label} className="v8-barrow"><div><b>{m.label}</b><small>{m.n_observed} recorded · {m.percent.toFixed(1)}% unweighted</small></div><div className="v8-bartrack"><span style={{width:m.weighted_percent+'%'}}/></div><strong>{m.weighted_percent.toFixed(1)}%</strong></div>):<p className="v7-empty">No indicators meet the group-level reporting threshold.</p>}</div>
    </Box>
   </div>
   <div className="v7-info"><Info size={18}/> Group summaries use survey weights. Intervals and population inference require full complex-survey design analysis. Suppressed cells are not shown.</div>
  </>}
  {page==='Patient assessment'&&<>
   <Header eyebrow="STRUCTURED HEALTH PROFILE" title="Patient assessment" description="Enter de-identified observations to create a live descriptive health snapshot. No personal prediction is calculated or stored."/>
   <InferenceReadinessV37 profile={profile} onExplore={()=>setPage('Model evidence')}/>
   <ClinicalOutcomeRegistryV38/>
   <ReadinessEvidenceV39/>
   <DoctorJourneyV36 profile={profile} visits={visits} onViewFollowUp={()=>setPage('Visit history')}/>
   <div className="v7-info"><ShieldCheck size={18}/> Use de-identified information only. Do not enter patient names, dates of birth, addresses or record numbers into this public research portal.</div>
   <div className="v7-profile-layout"><div className="v7-profile-form">
     <Box title="Background and measurements"><div className="v7-form-grid">
       <label>Age <input type="number" min="65" max="110" step="1" placeholder="Age" aria-invalid={profile.age!==''&&!isValidAssessment('age',profile.age||'')} value={profile.age||''} onChange={e=>setField('age',e.target.value)} /></label>
       <label>Sex <select value={profile.sex||''} onChange={e=>setField('sex',e.target.value)}><option value="">Not recorded</option><option>Female</option><option>Male</option></select></label>
       <label>BMI (kg/m²) <input type="number" step="0.1" min="10" max="70" placeholder="e.g. 26.5" aria-invalid={profile.bmi!==''&&!isValidAssessment('bmi',profile.bmi||'')} value={profile.bmi||''} onChange={e=>setField('bmi',e.target.value)} /></label>
       <label>PHQ-9 score <input type="number" step="1" min="0" max="27" placeholder="0–27" aria-invalid={profile.phq9_score!==''&&!isValidAssessment('phq9_score',profile.phq9_score||'')} value={profile.phq9_score||''} onChange={e=>setField('phq9_score',e.target.value)} /></label>
       </div></Box>
     <Box title="Physical function"><div className="v7-form-grid">{MOBILITY.map(k=><label key={k}>{LABELS[k]}<select value={profile[k]||''} onChange={e=>setField(k,e.target.value)}><option value="">Not recorded</option><option>No difficulty</option><option>Some difficulty</option><option>Much difficulty</option><option>Unable to do</option><option>Does not do activity</option><option>Not asked (structural skip)</option><option>Refused</option><option>Don't know</option></select></label>)}</div><p className="v7-fine">Activity nonparticipation, structural skip and refusal are distinct missingness/status categories, not ordered difficulty severities.</p></Box>
     <Box title="Health history" desc="A missing response is not treated as a negative response"><div className="v7-form-grid">{CHRONIC.map(k=><label key={k}>{LABELS[k]}<select value={profile[k]||''} onChange={e=>setField(k,e.target.value)}><option value="">Not recorded</option><option>Yes</option><option>No</option></select></label>)}</div></Box>
     <button className="v7-clear" onClick={()=>setProfile({})}><Trash2 size={16}/> Clear assessment</button>
    </div><div className="v7-profile-sidebar"><Box title="Assessment summary"><div className="v7-completion"><strong>{recorded} / {total}</strong><span>valid fields recorded</span></div>{invalidEntries.length>0&&<p role="alert" className="v7-fine">{invalidEntries.length} numeric field(s) are outside the permitted range or not integers. Correct them before counting this assessment as complete.</p>}<div className="v7-completion-track" role="progressbar" aria-label="Valid assessment fields" aria-valuemin={0} aria-valuemax={total} aria-valuenow={recorded}><i style={{width:100*recorded/total+'%'}}/></div><div className="v7-summary-line"><span>Health history entries marked Yes</span><strong>{present.length}</strong></div><div className="v7-summary-line"><span>Mobility items reporting difficulty</span><strong>{mobility.length}</strong></div><div className="v7-summary-line"><span>Fields unrecorded</span><strong>{total-recorded}</strong></div><p className="v7-fine">This is a descriptive summary of entered measurements, not a disease count or predictive score.</p></Box>
       <Box title="Recorded observations">{recorded===0?<p className="v7-empty">No measurements entered. Select a field to begin a new assessment.</p>:<div className="v7-values">{Object.entries(LABELS).filter(([k])=>isValidAssessment(k,profile[k]||'')).map(([k,label])=><div key={k}><span>{label}</span><strong>{profile[k]}</strong></div>)}</div>}</Box>
       <Box title="Research model status"><div className="v7-research-status"><Info size={20}/><div><strong>Population-level evidence available</strong><p>The current NHANES benchmark evaluates all-cause mortality across survey participants. This profile does not calculate an individual risk estimate.</p></div></div></Box>
    </div></div>
  </>}
  {page==='Visit history'&&<>
    <Header eyebrow="LONGITUDINAL MEASUREMENTS" title="Follow-up measurements" description="Reuse assessment measurements, add dated observations, and see actual changes in this browser session. No records are fetched from a database."/>
   <FollowUpSummaryV36 visits={visits}/>
    <div className="v7-two"><Box title="Record a visit" desc="Temporary de-identified assessment information"><div className="v7-form-grid"><label>Visit date<input type="date" value={visitDate} onChange={e=>setVisitDate(e.target.value)}/></label><label>BMI (kg/m²)<input type="number" min="10" max="70" step="0.1" placeholder="Optional" value={visitBmi} onChange={e=>setVisitBmi(e.target.value)}/></label><label>PHQ-9 score<input type="number" min="0" max="27" step="1" placeholder="Optional" value={visitPhq} onChange={e=>setVisitPhq(e.target.value)}/></label></div><button type="button" className="v36-prefill" disabled={!(isValidAssessment('bmi',profile.bmi||'')||isValidAssessment('phq9_score',profile.phq9_score||''))} onClick={()=>{setVisitBmi(isValidAssessment('bmi',profile.bmi||'')?profile.bmi:'');setVisitPhq(isValidAssessment('phq9_score',profile.phq9_score||'')?profile.phq9_score:'');}}>Use assessment measurements</button><button className="v7-primary" disabled={!visitDate||(!visitBmi&&!visitPhq)} onClick={addVisit}><Plus size={17}/> Add visit</button><p className="v7-fine">One entry per date. Re-entering a date replaces that visit. Data are cleared when the page reloads.</p></Box>
    <Box title="Visit summary">{visits.length?<><div className="v7-completion"><strong>{visits.length}</strong><span>dated assessments entered</span></div><div className="v7-visit-list">{trend.map(v=><div key={v.date}><span>{v.date}</span><span>BMI {v.bmi===null?'—':v.bmi}</span><span>PHQ-9 {v.phq===null?'—':v.phq}</span><button aria-label={'Remove visit '+v.date} onClick={()=>setVisits(all=>all.filter(x=>x.date!==v.date))}><Trash2 size={15}/></button></div>)}</div></>:<p className="v7-empty">No visits recorded. The graphs appear when measurements are added.</p>}</Box></div>
    {visits.length>0&&<div className="v7-two"><Box title="Body mass index across visits"><div className="v7-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={trend}><CartesianGrid stroke="#e8f0ed" strokeDasharray="4 4"/><XAxis dataKey="period" tick={{fontSize:11}}/><YAxis domain={['auto','auto']}/><Tooltip/><Line dataKey="bmi" stroke="#248a7a" strokeWidth={3} connectNulls={false} name="BMI"/></LineChart></ResponsiveContainer></div></Box><Box title="PHQ-9 score across visits"><div className="v7-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={trend}><CartesianGrid stroke="#e8f0ed" strokeDasharray="4 4"/><XAxis dataKey="period" tick={{fontSize:11}}/><YAxis domain={[0,27]}/><Tooltip/><Line dataKey="phq" stroke="#6080a0" strokeWidth={3} connectNulls={false} name="PHQ-9"/></LineChart></ResponsiveContainer></div></Box></div>}
  </>}
   {page==='Model evidence'&&<>
     <Header eyebrow="HOW THE ENGINE WOULD WORK" title="How an assessment becomes an explanation" description="A visual walkthrough for nontechnical readers. It illustrates the process; it does not run NHANES inference or attribute real model effects."/>
     <PredictionStoryV36 profile={profile}/>
     <FictionalScoringLabV37/>
     <FictionalMultiOutcomeLabV38/>
     <SyntheticServerV40/>
     <ValidationGateV41/>
     <ModelTranslationV42/>
     <ArtifactAcceptanceV43/>
     <StudyHandoffV44/>
  </>}
  </div>
  <footer className="v7-portal-foot">FrailtyScope · CDC/NCHS NHANES linked mortality · Population research · Not a clinical prediction service</footer>
 </div>;
}
