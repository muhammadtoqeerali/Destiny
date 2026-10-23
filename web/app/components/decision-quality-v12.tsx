'use client';
import {useMemo,useState} from 'react';
import {CartesianGrid,Legend,ResponsiveContainer,Tooltip,XAxis,YAxis,Bar,BarChart} from 'recharts';
import research from '../../public/data/nhanes-decision-quality-v12.json';
import { ThresholdSensitivityChart } from './threshold-sensitivity-chart';

type Quality=typeof research;
const report=research as Quality;
const pct=(v:number)=>(100*v).toFixed(1)+'%';
const fmt=(v:number|null,dec=3)=>v===null?'—':Number(v).toFixed(dec);
const locked=report.locked_threshold;
const closest=report.thresholds.reduce((a,b)=>Math.abs(a.threshold-locked)<Math.abs(b.threshold-locked)?a:b);
function Panel({title,sub,children}:{title:string;sub?:string;children:React.ReactNode}){
 return <section className="v7-card"><div className="v7-cardhead"><h3>{title}</h3>{sub&&<p>{sub}</p>}</div>{children}</section>;
}
function DataTable({cols,rows}:{cols:string[];rows:(string|number)[][]}){
 return <div className="v7-table-wrap"><table className="v7-table"><thead><tr>{cols.map((c,i)=><th key={i}>{c}</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr key={i}>{r.map((x,j)=><td key={j}>{x}</td>)}</tr>)}</tbody></table></div>;
}
export function DecisionQualityV12(){
 const [selectedThreshold,setSelectedThreshold]=useState(String(closest.threshold));
 const [dimension,setDimension]=useState<'Age'|'Sex'>('Age');
 const [mode,setMode]=useState<'tradeoff'|'benefit'>('tradeoff');
 const threshold=report.thresholds.find(x=>String(x.threshold)===selectedThreshold)||closest;
 const subgroup=useMemo(()=>report.subgroups.filter(x=>x.dimension===dimension),[dimension]);
 const bands=useMemo(()=>report.calibration_bands.filter(x=>x.dimension===dimension),[dimension]);
 const groupNames=Array.from(new Set(bands.map(x=>x.group)));
 const [group,setGroup]=useState<string>('80+');
 const shownGroup=groupNames.includes(group)?group:groupNames[0];
 const chosenBands=bands.filter(x=>x.group===shownGroup);
 return <div className="v11-lab v12-lab">
   <div className="v7-heading"><span className="nh-kicker">MODEL EVALUATION & DECISION QUALITY</span>
    <h2>Robustness, error trade-offs and calibration</h2>
    <p>Historical development-selected model and threshold; 2013–2014 observations were previously inspected in earlier releases. These are published NHANES aggregates, not fresh independent validation.</p></div>
   <div className="v11-metrics">
    <div className="v11-metric"><small>Later-cycle sample</small><strong>{report.counts.evaluation.toLocaleString()}</strong><span>{report.counts.events} observed events</span></div>
    <div className="v11-metric"><small>Discrimination</small><strong>{fmt(report.evaluation.roc_auc,3)}</strong><span>ROC-AUC · unchanged fitted model</span></div>
    <div className="v11-metric"><small>Probability accuracy</small><strong>{fmt(report.evaluation.brier,3)}</strong><span>Brier score · lower is better</span></div>
    <div className="v11-metric"><small>Locked decision threshold</small><strong>{fmt(locked,2)}</strong><span>Chosen during development, not from evaluation</span></div>
   </div>
   <Panel title="Exploratory uncertainty around historical evaluation" sub="95% exploratory participant-IID bootstrap percentile intervals. These are not NHANES survey-design-adjusted confidence intervals.">
    <DataTable cols={['Statistic','Point estimate','Lower 95%','Upper 95%']} rows={report.uncertainty.intervals.map(x=>[
      x.metric.replaceAll('_',' '),fmt(x.estimate,4),fmt(x.lower,4),fmt(x.upper,4)])}/>
    <p className="v11-fine">{report.uncertainty.replicates} bootstrap resamples · no model retraining · no claim of external clinical validation.</p>
   </Panel>
   <Panel title="Threshold sensitivity and false-positive burden" sub="Explore outcomes at fixed thresholds; changing this control never changes the selected model or the development-locked operating threshold.">
    <div className="v12-controls"><label>Inspect threshold
      <select className="v11-select" value={selectedThreshold} onChange={(e:{target:{value:string}})=>setSelectedThreshold(e.target.value)}>
      {report.thresholds.map(x=><option key={x.threshold} value={String(x.threshold)}>{fmt(x.threshold,2)}{Math.abs(x.threshold-locked)<0.00001?' · selected':''}</option>)}
      </select></label>
      <label>View
       <select className="v11-select" value={mode} onChange={(e:{target:{value:string}})=>setMode(e.target.value as 'tradeoff'|'benefit')}>
         <option value="tradeoff">Sensitivity and false-positive rate</option><option value="benefit">Decision-curve net benefit</option>
       </select>
      </label>
    </div>
    <div className="v11-chart" style={{height:'auto',minHeight:280}}>
      <ThresholdSensitivityChart data={report.thresholds} selected={threshold.threshold} mode={mode}/>
    </div>
    <div className="v12-statrow">
      <div><span>Sensitivity</span><strong>{pct(threshold.recall)}</strong></div>
      <div><span>False-positive rate</span><strong>{pct(threshold.false_positive_rate)}</strong></div>
      <div><span>Precision</span><strong>{pct(threshold.precision)}</strong></div>
      <div><span>Flagged observations</span><strong>{threshold.predicted_positive}</strong></div>
    </div>
    <p className="v11-fine">Net benefit weights false positives by threshold odds, reflecting an assumed cost trade-off. These thresholds are exploratory and are not recommendations for clinical intervention.</p>
   </Panel>
   <div className="v7-two"><Panel title="Age and sex subgroup error audit" sub="Discrimination, sensitivity and false-positive rate calculated at the one locked threshold.">
      <div className="v12-controls"><label>Stratification
       <select className="v11-select" value={dimension} onChange={(e:{target:{value:string}})=>setDimension(e.target.value as 'Age'|'Sex')}><option>Age</option><option>Sex</option></select>
      </label></div>
      <DataTable cols={['Group','n','Observed events','AUC','Recall','False-positive rate']} rows={subgroup.map(x=>[
          x.group,x.n,x.events,fmt(x.roc_auc),pct(x.recall),pct(x.false_positive_rate)])}/>
      <p className="v11-fine">Groups require at least 100 records and 20 events and 20 non-events. Subgroup variation does not establish clinical fairness or causal differences.</p>
    </Panel>
    <Panel title="Group-level probability reliability" sub="Compare observed outcome frequency with the average predicted risk, using the unchanged model.">
      <div className="v11-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={subgroup} margin={{top:10,left:0,right:0,bottom:5}}>
        <CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="group" tick={{fontSize:11}}/><YAxis tickFormatter={pct}/><Tooltip formatter={(v:unknown)=>pct(Number(v))}/><Legend/>
        <Bar dataKey="observed_event_rate" name="Observed event rate" fill="#278e82"/>
        <Bar dataKey="mean_predicted_risk" name="Mean predicted risk" fill="#ba734e"/>
      </BarChart></ResponsiveContainer></div>
      <p className="v11-fine">The two bars should be compared within each group. Group-level agreement does not imply well-calibrated predictions for individual respondents.</p>
    </Panel></div>
   <Panel title="Within-group calibration across risk bands" sub="Each age/sex group is ranked separately by predicted risk. Bands with small outcome counts are withheld.">
    {groupNames.length>0?<>
      <div className="v12-controls"><label>Group
       <select className="v11-select" value={shownGroup} onChange={(e:{target:{value:string}})=>setGroup(e.target.value)}>{groupNames.map(x=><option key={x}>{x}</option>)}</select>
       </label></div>
      <DataTable cols={['Risk band (low → high)','n','Average predicted','Observed event rate']} rows={chosenBands.map(x=>[
        `Band ${x.band}`,x.n,pct(x.mean_predicted_risk),pct(x.observed_event_rate)])}/>
    </>:<p className="v11-fine">No risk bands meet the predeclared minimum denominators and outcome counts for publication.</p>}
    <p className="v11-fine">Some bands are suppressed when they contain fewer than 50 records or fewer than 10 events or non-events. No individual records are displayed.</p>
   </Panel>
   {report.experiments&&<Panel title="Distinct historical experiments: descriptive comparison" sub="All results use a later-cycle cohort of 1,257 with 246 outcomes. Model-building protocols differ; this is not a paired significance test.">
      <DataTable cols={['Experiment','ROC-AUC','Brier','Recall','Precision','False positives','Threshold']} rows={report.experiments.rows.map(x=>[
        x.experiment,fmt(x.roc_auc,4),fmt(x.brier,4),pct(x.recall),pct(x.precision),x.false_positives,x.threshold===null?'—':fmt(x.threshold,3)])}/>
      <p className="v11-fine">{report.experiments.limitation}</p>
   </Panel>}
   <Panel title="Evaluation boundaries"><div className="v7-checks">{report.limitations.map((x,i)=><div key={i}><span>{x}</span></div>)}</div></Panel>
  </div>;
}
