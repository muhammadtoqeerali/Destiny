'use client';
import {FlaskConical, Info, ShieldCheck} from 'lucide-react';
import {Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis} from 'recharts';
import mobility from '../data/real-mobility-summary-v49.json';
const pct=(x:number)=>`${(x*100).toFixed(1)}%`;
const short=(name:string)=>name==='Histogram gradient boosting'?'Hist. boosting':name==='Logistic regression'?'Logistic':name==='Random forest'?'Random forest':name==='Dummy prior'?'Dummy':name;
const pretty=(f:string)=>f==='phq9_score'?'PHQ-9 score':f.replaceAll('_',' ');

/** Aggregate public survey evidence only. Never attaches it to fictional person-level predictions. */
export function RealMobilityDoctorV49(){
 const dev=mobility.cohorts['2015-2016'];
 const later=mobility.cohorts['2017-2018'];
 return <section className="v49-doctor-evidence" aria-label="Real NHANES population research snapshot">
  <div className="if-section-head"><div><span className="if-caption">REAL SURVEY FINDINGS · SEPARATE FROM THE FICTIONAL PROFILES BELOW</span><h2>What did older adults report about walking?</h2><p>NHANES public-use surveys, age 65+. This describes <strong>current difficulty walking a quarter mile</strong>—not who will develop frailty later.</p></div><span className="v49-data-tag">Population research</span></div>
  <div className="v49-doctor-facts">
   <div><small>Earlier survey · 2015–2016</small><strong>{dev.questionnaire_respondents.toLocaleString()}</strong><span>respondents · {pct(dev.observed_event_fraction)} reported difficulty</span></div>
   <div><small>Later survey · 2017–2018</small><strong>{later.questionnaire_respondents.toLocaleString()}</strong><span>respondents · {pct(later.observed_event_fraction)} reported difficulty</span></div>
   <div><small>Model evaluation</small><strong>{mobility.evaluation.roc_auc.toFixed(3)}</strong><span>ROC-AUC for classifying current reported difficulty, exploratory later-cycle evaluation</span></div>
  </div>
  <p className="v49-doctor-caution"><Info size={16}/> These are unweighted descriptive fractions from the eligible survey subset—not national prevalence, diagnoses or predictions for the fictional examples shown below. The later survey was previously inspected; clinical use is not supported.</p>
 </section>
}

export function RealMobilityAdminV49(){
 const selected=mobility.models.find(x=>x.name===mobility.selected_model)!;
 const later=mobility.cohorts['2017-2018'];
 const chart=mobility.models.map(x=>({name:short(x.name),brier:x.validation_brier}));
 const important=mobility.permutation_importance.map(x=>({name:pretty(x.feature),value:x.delta_brier}));
 return <div className="v49-admin-results" role="region" aria-label="Real NHANES mobility experiment results">
  <section className="if-card"><div className="if-section-head"><div><span className="if-caption">02 · VERIFIED AGGREGATE RESEARCH RESULT · 2015–2018</span><h2>Real NHANES: current walking difficulty</h2><p>Different people were surveyed in each cycle. We classify <strong>difficulty already reported</strong>; we do not predict future frailty or a future diagnosis.</p></div><span className="v49-data-tag">Real public data</span></div>
   <div className="if-mini-stats if-inner-stats"><div><span>Development survey</span><b>{mobility.cohorts['2015-2016'].questionnaire_respondents}</b><small>2015–2016 · age 65+</small></div><div><span>Later-cycle survey</span><b>{later.questionnaire_respondents}</b><small>2017–2018 · previously inspected</small></div><div><span>Later-cycle difficulty</span><b>{later.target_events}</b><small>{pct(later.observed_event_fraction)} of eligible respondents (unweighted)</small></div></div>
   <div className="if-method"><div><b>Source &amp; endpoint</b><span>CDC NHANES public-use XPT; PFQ061B: no difficulty (1) versus difficulty (2–4). PFQ054 routing skips and unanswered items excluded.</span></div><div><b>Inputs</b><span>{mobility.predictors.map(pretty).join(', ')} · age 80+ is top-coded.</span></div><div><b>Preprocessing</b><span>Decoded exact SAS XPORT zeros; nine-item complete PHQ-9; missing-value handling and numeric/categorical transformations fitted on training data only.</span></div><div><b>Partitions</b><span>Earlier-cycle train {mobility.split.development_fit_n} / selection {mobility.split.development_selection_n}; later-cycle evaluation {mobility.split.later_cycle_test_n}. No survey respondent appears in both cycles.</span></div><div><b>Model selection</b><span>Compare six candidate families on the same development validation subset; choose lowest validation Brier, not highest later-cycle AUC.</span></div></div>
  </section>
  <section className="if-card"><div className="if-section-head"><div><span className="if-caption">03 · FAIR MODEL COMPARISON</span><h2>Why CatBoost was selected</h2><p>CatBoost achieved the lowest validation Brier ({selected.validation_brier.toFixed(5)}). Logistic regression had the lower cross-validation Brier; the advantage is not universal.</p></div></div>
   <div className="v49-chart" role="img" aria-label="Bar chart of six validation Brier scores, lowest is CatBoost"><ResponsiveContainer width="100%" height="100%"><BarChart data={chart} margin={{top:8,right:14,bottom:6,left:-5}}><CartesianGrid vertical={false} stroke="#e7eef0" strokeDasharray="3 3"/><XAxis dataKey="name" tick={{fontSize:10}} interval={0} angle={-15} textAnchor="end" height={70}/><YAxis domain={[0,0.2]} tick={{fontSize:11}}/><Tooltip formatter={(v)=>typeof v==='number'?v.toFixed(5):'—'}/><Bar dataKey="brier" name="Validation Brier ↓" fill="#257783" radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></div>
   <div className="if-table-wrap"><table><thead><tr><th>Candidate</th><th>3-fold CV Brier ↓</th><th>Validation AUC ↑</th><th>Validation Brier ↓</th><th>Decision</th></tr></thead><tbody>{mobility.models.map(m=><tr key={m.name}><td><strong>{m.name}</strong></td><td>{m.cv_brier.toFixed(5)}</td><td>{m.validation_auc.toFixed(5)}</td><td>{m.validation_brier.toFixed(5)}</td><td>{m.name===mobility.selected_model?'Selected':'Compared'}</td></tr>)}</tbody></table></div>
   <p className="if-muted">No claim of state-of-the-art ranking across unrelated studies; identical dataset, target and selection partition are required for this comparison.</p>
  </section>
  <section className="if-card"><div className="if-section-head"><div><span className="if-caption">04 · EXPLORATORY LATER-CYCLE RESULTS</span><h2>Performance, uncertainty and calibration</h2><p>CatBoost evaluated on 2017–2018. This survey cycle was already inspected during the v0.48 correction sequence, so this is <strong>not an untouched independent test</strong>.</p></div></div>
   <div className="v49-metric-grid"><div><small>ROC-AUC</small><b>{mobility.evaluation.roc_auc.toFixed(3)}</b><span>Naive row bootstrap 95% interval: {mobility.naive_row_bootstrap_95pct.roc_auc.map(x=>x.toFixed(3)).join('–')}</span></div><div><small>Average precision</small><b>{mobility.evaluation.average_precision.toFixed(3)}</b><span>Later-cycle prevalence {pct(later.observed_event_fraction)}</span></div><div><small>Brier score ↓</small><b>{mobility.evaluation.brier.toFixed(3)}</b><span>Naive interval: {mobility.naive_row_bootstrap_95pct.brier.map(x=>x.toFixed(3)).join('–')}</span></div><div><small>Sensitivity at 0.5</small><b>{pct(mobility.evaluation.sensitivity_at_0_5)}</b><span>Low; not suitable as a validated screening rule</span></div><div><small>Specificity at 0.5</small><b>{pct(mobility.evaluation.specificity_at_0_5)}</b><span>Default cutoff is not clinically optimized</span></div><div><small>Weighted Brier · exploratory</small><b>{mobility.survey_weighted_brier_exploratory.brier.toFixed(3)}</b><span>Survey-design variance not estimated</span></div></div>
   <h3 className="if-subhead">Predicted versus observed in reported calibration bins</h3>
   <div className="v49-cal-list">{mobility.calibration.map(b=><div key={b.range.join('-')}><div><strong>{pct(b.range[0])}–{pct(b.range[1])}</strong><small>n={b.n}</small></div><div className="v49-cal-bars"><span>Predicted {pct(b.mean_predicted)}</span><i style={{width:pct(b.mean_predicted)}}/><span>Observed {pct(b.observed_fraction)}</span><i className="v49-observed" style={{width:pct(b.observed_fraction)}}/></div></div>)}</div>
   <p className="if-muted">Reported bins include {mobility.calibration.reduce((acc,b)=>acc+b.n,0)} people; {mobility.unshown_calibration_n} are omitted by the minimum-bin-size display rule. In the 20–40% band the mean score is 28.2% against 35.3% observed, indicating underprediction.</p>
  </section>
  <section className="if-card"><div className="if-section-head"><div><span className="if-caption">05 · INTERPRETABILITY / LIMITATIONS</span><h2>What influences this model?</h2><p>Permutation importance measures how much shuffling each feature worsens validation Brier score. It is <strong>not a causal explanation or individual-level attribution</strong>.</p></div></div>
   <div className="v49-importance-list">{important.map(item=><div key={item.name}><span>{item.name}</span><div aria-label={`${item.name}: validation Brier increase ${item.value.toFixed(4)}`}><i style={{width:`${Math.max(1,item.value/important[0].value*100)}%`}}/></div><b>{item.value.toFixed(4)}</b></div>)}</div>
   <div className="v49-limits"><ShieldCheck size={18}/><div><b>What we can claim</b><p>A reproducible, real public-data demonstration of cross-sectional mobility classification and model comparison, with observed generalization limitations.</p><b>What we cannot claim</b><p>No future frailty prediction, HUNT validation, causation, real patient inference or clinical screening suitability. Complex NHANES survey variance was not modeled and the later cycle is previously inspected.</p></div></div>
  </section>
  <p className="if-endnote"><FlaskConical size={16}/> Source code and aggregate figures are reproducible; individual NHANES records, model artifacts, and HUNT/NHATS/SHARE data are not included in the public app.</p>
 </div>;
}
