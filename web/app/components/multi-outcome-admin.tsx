'use client';
import { useState } from 'react';
import { Activity, ArrowRight, BookOpen, BrainCircuit, Database, ExternalLink, HeartPulse, Info, ShieldCheck } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import future from '../../public/data/multioutcome-demo.json';
import shapDemo from '../../public/data/shap-summary-demo.json';
import { DeveloperWorkspace } from '../workspaces';

type Outcome = (typeof future.outcomes)[number];
type HubView = 'Outcomes & results' | 'Model comparison' | 'Explainability' | 'HUNT readiness' | 'Original pipeline';
const views:HubView[]=['Outcomes & results','Model comparison','Explainability','HUNT readiness','Original pipeline'];
const scores=(n:number)=>n.toFixed(3);

export function AdminResearchHub(){
 const [view,setView]=useState<HubView>('Outcomes & results');
 const [selected,setSelected]=useState(0);
 const outcome:Outcome=future.outcomes[selected];
 const variants=outcome.status==='evaluated'?outcome.validationModels:[];
 return <div className="multi-admin">
  <div className="multi-intro"><div className="multi-eyebrow"><BrainCircuit size={17}/> RESEARCH STUDIO / MULTI-OUTCOME ANALYTICS</div><h1>Explore the whole ageing-health picture.</h1><p>Five separately evaluated outcome models, systematic benchmarking and readiness for approved longitudinal HUNT data.</p></div>
  <div className="multi-caution"><Info size={18}/><div><b>Research demonstration only.</b> These models were trained on simulated participants with invented event outcomes. The HUNT figures shown below are publicly reported cohort aggregates, not inputs to these models.</div></div>
  <div className="multi-top-tabs" role="tablist" aria-label="Admin research views">{views.map(t=><button key={t} role="tab" aria-selected={view===t} className={view===t?'current':''} onClick={()=>setView(t)}>{t}</button>)}</div>
  {view==='Outcomes & results'&&<>
   <div className="multi-kpis"><article><small>Demo participants</small><strong>{future.summary.syntheticParticipants.toLocaleString()}</strong><span>Fictional records</span></article><article><small>Future outcome targets</small><strong>{future.outcomes.length}</strong><span>Separate experimental models</span></article><article><small>Algorithms compared</small><strong>{future.summary.algorithms.length}</strong><span>Logistic, HGB, XGBoost, CatBoost</span></article><article><small>Reserved test sample</small><strong>{future.summary.split.test.toLocaleString()}</strong><span>Common person-level split</span></article></div>
   <div className="multi-title"><span>FIVE OUTCOME DOMAINS</span><h2>Choose an outcome to inspect</h2><p>Different future events require independent evidence and different model evaluation.</p></div>
   <div className="multi-outcome-picker">{future.outcomes.map((o,i)=><button key={o.id} onClick={()=>setSelected(i)} className={selected===i?'current':''}><span>{'0'+(i+1)}</span><b>{o.label}</b><small>{o.status==='evaluated'?'Model evaluated':'Not estimable'}</small></button>)}</div>
   {outcome.status==='evaluated'&&<div className="multi-dual"><section className="multi-panel"><div className="multi-panel-head"><b>{outcome.label} · held-out evaluation</b><small>Only synthetic outcomes · never a real prognosis</small></div><div className="multi-outcome-stats"><div><small>ROC-AUC</small><strong>{scores(outcome.test.roc_auc)}</strong><span>Ranking</span></div><div><small>Avg. precision</small><strong>{scores(outcome.test.average_precision)}</strong><span>Positive-case prioritization</span></div><div><small>Brier</small><strong>{scores(outcome.test.brier)}</strong><span>Probability error ↓</span></div><div><small>Accuracy at 0.5</small><strong>{(outcome.test.accuracy*100).toFixed(1)}%</strong><span>Threshold-specific; can mislead</span></div></div><div className="multi-selected">Selected: <strong>{outcome.selectedModel}</strong> based on validation Brier score</div></section>
    <section className="multi-panel"><div className="multi-panel-head"><b>Probability calibration</b><small>Test-set bins for this outcome</small></div><div className="multi-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={outcome.calibration}><CartesianGrid stroke="#edf2f0" strokeDasharray="3 3"/><XAxis dataKey="expected" tick={{fontSize:11}}/><YAxis tick={{fontSize:11}}/><Tooltip/><Bar name="Observed event fraction" dataKey="observed" fill="#238d84" radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></div><small className="multi-caption">Calibration should be reviewed with bin sizes; a bar chart does not establish real-world validity.</small></section></div>}
   <div className="multi-panel"><div className="multi-panel-head"><b>Why high accuracy alone is misleading</b><small>Fractions of events differ across outcomes</small></div><p className="multi-description">A model can achieve high accuracy by predicting the majority non-event class. For example, the synthetic fracture task achieves high accuracy at the 0.5 cutoff but substantially lower ROC-AUC. Consider calibration, sensitivity, specificity, prevalence and decision value together.</p></div>
  </>}
  {view==='Model comparison'&&<><div className="multi-title"><span>MODEL EVALUATION</span><h2>Transparent benchmark table</h2><p>Validation results choose a model. The test set is reported afterward, never used to pick the winner.</p></div>
   <div className="multi-table-wrap"><table className="multi-table"><thead><tr><th>Outcome</th><th>Selected model</th><th>Test ROC-AUC</th><th>Average precision</th><th>Brier ↓</th><th>Accuracy*</th></tr></thead><tbody>{future.outcomes.filter(o=>o.status==='evaluated').map(o=><tr key={o.id}><td><b>{o.label}</b></td><td>{o.selectedModel}</td><td>{scores(o.test.roc_auc)}</td><td>{scores(o.test.average_precision)}</td><td>{scores(o.test.brier)}</td><td>{(o.test.accuracy*100).toFixed(1)}%</td></tr>)}</tbody></table></div>
   <p className="multi-caption">* Accuracy uses a fixed 0.5 threshold, not a clinically optimized threshold. These are invented synthetic-data experiments; none of the figures are HUNT findings.</p>
   <div className="multi-title"><h2>Compare model families</h2><p>Select an outcome to see which algorithms were tested on its validation cohort.</p></div>
   <select className="multi-select" value={selected} onChange={e=>setSelected(Number(e.target.value))}>{future.outcomes.map((o,i)=><option key={o.id} value={i}>{o.label}</option>)}</select>
   <div className="multi-table-wrap"><table className="multi-table"><thead><tr><th>Algorithm</th><th>Validation ROC-AUC</th><th>Validation Brier ↓</th><th>Validation recall (0.5)</th></tr></thead><tbody>{variants.map(v=><tr key={v.name}><td>{v.name}{v.name===outcome.selectedModel?' ✓':''}</td><td>{scores(v.validation.roc_auc)}</td><td>{scores(v.validation.brier)}</td><td>{(v.validation.recall*100).toFixed(1)}%</td></tr>)}</tbody></table></div>
   <div className="multi-caution"><Info size={18}/><span>Model comparison is a benchmark, not a demonstration of medical benefit. The generated data's event process is known by construction; real performance may differ substantially.</span></div>
  </>}
  {view==='Explainability'&&<><div className="multi-title"><span>TRUE MODEL-ATTRIBUTION CALCULATION</span><h2>SHAP: global feature-response summary</h2><p>Permutation SHAP was actually computed for five simulated test cases per selected model. These attributes describe model output, not disease mechanisms.</p></div>
   <select className="multi-select" value={selected} onChange={e=>setSelected(Number(e.target.value))}>{future.outcomes.map((o,i)=><option key={o.id} value={i}>{o.label}</option>)}</select>
   <div className="multi-panel"><div className="multi-panel-head"><b>Mean absolute SHAP · {outcome.label}</b><small>Top predictors on transformed inputs, probability scale. n=5 synthetic cases (exploratory only).</small></div>
    <div className="multi-shap-list">{(shapDemo.outcomes.find(x=>x.id===outcome.id)?.features||[]).slice(0,8).map(x=><div key={x.name}><span>{x.name.replace('num__','').replace('cat__','').replaceAll('_',' ')}</span><div><i style={{width:Math.max(2,Math.min(100,x.mean_abs_shap/.07*100))+'%'}}/></div><strong>{x.mean_abs_shap.toFixed(4)}</strong></div>)}</div>
    <p className="multi-caption">SHAP values reflect changes in the model's predicted probability relative to sampled background examples. They are not causal effects, treatment instructions or patient-specific clinical explanations. Five records are too few to establish stable global ranking.</p></div>
   <div className="multi-caution"><Info size={18}/><span>The Doctor Portal presents separate one-feature response contrasts for selected fictional cases. Those case-level contrasts are NOT SHAP values; the methods must not be conflated.</span></div>
  </>}
  {view==='HUNT readiness'&&<><div className="multi-title"><span>PUBLICATION-GROUNDED CONTEXT</span><h2>What we know about the real HUNT4 70+ cohort</h2><p>These are genuine publicly reported sample sizes, not the rows used to train FrailtyScope.</p></div>
   <div className="multi-kpis"><article><small>HUNT4 70+ · original area</small><strong>{future.publishedHuntContext.originalAreaN.toLocaleString()}</strong><span>Published cohort count</span></article><article><small>HUNT4 Trondheim 70+</small><strong>{future.publishedHuntContext.trondheimN.toLocaleString()}</strong><span>Additional urban cohort</span></article></div>
   <div className="multi-panel"><div className="multi-panel-head"><b>Required data before real modeling</b><small>Patient-level access must be approved by NTNU/HUNT</small></div><div className="multi-check-grid">{[
      ['Approved access','Research ethics approval, HUNT Data Access Committee decision and signed project agreement.'],
      ['Feature mapping','Map delivered HUNT variable codes to approved standardized feature fields.'],
      ['Dated endpoints','Document incidents, baseline dates, follow-up dates and links to authorized registries.'],
      ['Censoring & competing events','Do not label loss to follow-up or early death as no event.'],
      ['Secure modeling','Fit approved data only inside the institutionally authorized computing environment.'],
      ['Non-disclosive reporting','Apply disclosure control and publication approvals to any external summary or figure.']
    ].map(([title,description])=><div key={title}><ShieldCheck size={20}/><span><b>{title}</b><small>{description}</small></span></div>)}</div>
   <a className="multi-source" href={future.publishedHuntContext.source} target="_blank" rel="noopener noreferrer"><BookOpen size={17}/> Read the published HUNT4 70+ cohort profile <ExternalLink size={14}/></a></div>
   <div className="multi-caution"><Database size={18}/><span>The public databank documents available variables but does not provide individual-level research data. FrailtyScope includes a LOCAL-ONLY authorized-data adapter; it never sends real participant data to Vercel.</span></div>
  </>}
  {view==='Original pipeline'&&<DeveloperWorkspace/>}
 </div>;
}
