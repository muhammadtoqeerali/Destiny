'use client';
import { useState } from 'react';
import { Activity, BrainCircuit, CalendarDays, HeartPulse, Info, ShieldAlert } from 'lucide-react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import research from '../../public/data/multioutcome-demo.json';

export function HealthOutlook({caseId}:{caseId:string}){
 const patient=research.cases.find(p=>p.id===caseId);
 const [selected,setSelected]=useState('all');
 if (!patient) return <div className="doctor-safety">Outlook unavailable for this simulated case.</div>;
 const shown=selected==='all'?patient.outcomes:patient.outcomes.filter(o=>o.id===selected);
 return <section className="multi-clinical-outlook">
  <div className="multi-title"><span>SIMULATED FOLLOW-UP / NOT CLINICAL PREDICTION</span><h2>Exploring possible future health domains</h2><p>Five independently modeled events across a fictional 12-month follow-up. The percentages represent artificial model outputs, not an individual's true future health.</p></div>
  <div className="multi-doctor-warning"><ShieldAlert size={22}/><span>All outcomes and trajectories shown below were generated for a software demonstration. Do not use these estimates for assessment, diagnosis, or treatment.</span></div>
  <label className="multi-outcome-filter">Health domain <select value={selected} onChange={e=>setSelected(e.target.value)}><option value="all">All modeled domains</option>{patient.outcomes.map(x=><option value={x.id} key={x.id}>{x.label}</option>)}</select></label>
  <div className="multi-doctor-outcomes">{shown.map(o=><div key={o.id} className="multi-doctor-outcome"><span className="multi-doctor-icon"><HeartPulse size={18}/></span><div><strong>{o.label}</strong><small>Illustrative model score · next {o.horizonMonths} months</small><div className="multi-doctor-bar"><i style={{width:`${o.score}%`}}/></div></div><b>{o.score.toFixed(1)}%</b></div>)}</div>
  {selected!=='all'&&shown[0]&&<section className="doctor-card"><div className="doctor-card-title"><span className="micro-label">EXAMPLE-LEVEL MODEL RESPONSE</span><h3>Which inputs changed this score?</h3><p>One feature is replaced by its typical value from the synthetic training cohort while other inputs are held fixed. These are not SHAP attributions or medical causes.</p></div><div className="multi-responses">{shown[0].responses.map(r=><div key={r.key}><span><b>{r.name}</b><small>Simulated measurement: {r.value}</small></span><strong>{r.delta_pp>=0?'+':''}{r.delta_pp.toFixed(1)} pp</strong></div>)}</div><p className="multi-caption">The response differences are non-additive, are sensitive to correlated features, and cannot establish what will happen to an actual patient.</p></section>}
  <section className="doctor-card multi-history"><div className="doctor-card-title"><span className="micro-label">PRE-BASELINE SIMULATION</span><h3>Illustrative past measurement changes</h3><p>Three simulated prior assessment points, included to show how a longitudinal clinical interface could work. NOT HUNT observations and NOT forecasts.</p></div>
   <div className="multi-history-grid"><div><h4>Walking speed (m/s)</h4><div className="multi-history-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={patient.priorVisits}><CartesianGrid stroke="#eff2f1" strokeDasharray="3 3"/><XAxis dataKey="period" tick={{fontSize:10}}/><YAxis domain={['auto','auto']} tick={{fontSize:11}}/><Tooltip/><Line dataKey="gait_ms" name="Walking speed" stroke="#21857c" strokeWidth={3}/></LineChart></ResponsiveContainer></div></div><div><h4>Cognition (MoCA demo score)</h4><div className="multi-history-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={patient.priorVisits}><CartesianGrid stroke="#eff2f1" strokeDasharray="3 3"/><XAxis dataKey="period" tick={{fontSize:10}}/><YAxis domain={['auto','auto']} tick={{fontSize:11}}/><Tooltip/><Line dataKey="moca" name="Cognition" stroke="#61899f" strokeWidth={3}/></LineChart></ResponsiveContainer></div></div></div>
   <p className="multi-caption"><CalendarDays size={15}/> Genuine progression analysis requires repeated participant measurements with verified observation dates and measurement comparability.</p>
  </section>
  <div className="doctor-card multi-interpret"><Info size={19}/><div><strong>What this screen does—and does not—mean</strong><p>Each model answers a separate artificial endpoint question. Higher displayed numbers do not diagnose a condition or guarantee a future outcome; they cannot be combined into a single frailty probability. The interface demonstrates how researchers and clinicians could examine distinct outcomes and historical trends once models are trained and independently validated on approved data.</p></div></div>
 </section>;
}
