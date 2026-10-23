'use client';
import { useMemo, useState } from 'react';
import { BarChart, Bar, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend, LineChart, Line } from 'recharts';
import audit from '../../public/data/nhanes-case-audit-v11.json';


type Summary=Record<'min'|'p01'|'q25'|'median'|'q75'|'p99'|'max',number>;
type Feature={feature:string;label:string;description:string;type:'numeric'|'categorical';observed:number;missing:number;missing_pct:number;unique:number;summary?:Summary;distribution?:{bin:string;n:number}[];distribution_suppressed_n?:number};
type Transform={feature:string;label:string;method:string;training_missing:number;validation_missing:number;after_missing:number;impute_value:string|number;center?:number;scale?:number;before_range?:Summary;after_range?:Summary;output_columns?:string[]};
type Metrics={n:number;roc_auc:number;average_precision:number;brier:number;accuracy:number;precision:number;recall:number;f1:number;threshold:number;confusion:{tn:number;fp:number;fn:number;tp:number}};
type Candidate={name:string;cv_score:number|null;validation:Metrics;parameters:Record<string,number|string>;fit_search_seconds:number};
type Audit={data_contract:{outcome:string;task:string;split:string;model_input_columns:number;excluded_from_predictors:string[]};
 data_integrity?:{phq9_observed_percent:number;source_check_mismatches:number;xport_zero_values_normalized:number;reporting:string}|null;counts:{all:number;train:number;validation:number;evaluation:number};features:Feature[];
 cohort_shift:{feature:string;standardized_mean_difference:number;development_missing_pct:number;evaluation_missing_pct:number}[];
 correlations:{a:string;b:string;spearman_rho:number}[];
 preprocessing:{input_feature_count:number;output_feature_count:number;methods:Transform[]};
 selection:{metric:string;model:string;candidates:Candidate[];permutation_importance_validation:{feature:string;mean_metric_drop:number}[];learning_curve:{train_n:number;training_brier:number;validation_brier:number}[]};
 evaluation:{metrics:Metrics;baseline:Metrics;calibration:{bin:number;n:number;predicted:number;observed:number}[];
 subgroups:{group:string;n:number;events:number;event_rate:number;roc_auc:number;recall:number;false_positive_rate:number;brier:number}[]};
 enhancement:{method:string;model:string;rule:{accepted:boolean;raw_validation_brier:number;crossfit_calibrated_brier:number;
 oof_brier_gain:number;required_min_brier_gain:number;raw_validation_auc:number;crossfit_calibrated_auc:number};
 thresholds:{original:number;selected:number};later_cycle:{original:Metrics;selected:Metrics}};
 methodology:{limitations:string[]}};
const workbench=audit as unknown as Audit;

type Stage='Dataset intelligence'|'Preprocessing'|'Model selection'|'Model mechanics'|'Enhancement'|'Evaluation';
const STAGES:Stage[]=['Dataset intelligence','Preprocessing','Model selection','Model mechanics','Enhancement','Evaluation'];
const pct=(x:number)=>`${(x*100).toFixed(1)}%`;
const fmt=(x:number|null|undefined,decimal=3)=>x===null||x===undefined?'—':x.toFixed(decimal);
const primary=workbench.selection.candidates.find(x=>x.name===workbench.selection.model)!;
const pass=workbench.enhancement.rule.accepted;
function Section({title,subtitle,children}:{title:string;subtitle?:string;children:React.ReactNode}){
 return <section className="v7-card"><div className="v7-cardhead"><h3>{title}</h3>{subtitle&&<p>{subtitle}</p>}</div>{children}</section>;
}
function Detail({name,value}:{name:string;value:string|number}){
 return <div className="v7-summary-line"><span>{name}</span><strong>{value}</strong></div>;
}
function Metric({label,value,context}:{label:string;value:string;context:string}){
 return <div className="v11-metric"><small>{label}</small><strong>{value}</strong><span>{context}</span></div>;
}
function Table({head,rows}:{head:string[];rows:(string|number)[][]}){
 return <div className="v7-table-wrap"><table className="v7-table"><thead><tr>{head.map((h,i)=><th key={i}>{h}</th>)}</tr></thead><tbody>{rows.map((row,i)=><tr key={i}>{row.map((v,j)=><td key={j}>{v}</td>)}</tr>)}</tbody></table></div>;
}
export function EvidenceWorkbenchV11(){
 const [stage,setStage]=useState<Stage>('Dataset intelligence');
 const [feature,setFeature]=useState('phq9_score');
 const [search,setSearch]=useState('');
 const item=workbench.features.find(x=>x.feature===feature)||workbench.features[0];
 const prep=workbench.preprocessing.methods.find(x=>x.feature===feature);
 const profileList=useMemo(()=>workbench.features.filter(x=>`${x.label} ${x.feature}`.toLowerCase().includes(search.toLowerCase())),[search]);
 const selectedModels=workbench.selection.candidates.map(c=>({name:c.name==='random_forest'?'RF':c.name==='hist_boost'?'HistBoost':c.name,
   brier:c.validation.brier,auc:c.validation.roc_auc??0,cv:c.cv_score}));
 return <div className="v11-lab">
   <div className="v7-heading"><span className="nh-kicker">DATA SCIENCE WORKBENCH</span>
    <h2>Dataset to model outcome</h2><p>Historical cohort analysis, fitted transformation evidence, model comparison, and previously inspected later-cycle evaluation; not fresh independent validation.</p></div>
   <nav className="v11-nav" aria-label="Analysis stages">{STAGES.map((s,i)=><button key={s} onClick={()=>setStage(s)} className={stage===s?'active':''}><small>{String(i+1).padStart(2,'0')}</small>{s}</button>)}</nav>
   {stage==='Dataset intelligence'&&<>
    <div className="v11-metrics"><Metric label="Study observations" value={workbench.counts.all.toLocaleString()} context="CDC public-use NHANES"/>
     <Metric label="Measured predictors" value={String(workbench.features.length)} context="Numeric and categorical"/>
     <Metric label="Development sample" value={String(workbench.counts.train+workbench.counts.validation)} context="2011–2012"/>
     <Metric label="Evaluation sample" value={String(workbench.counts.evaluation)} context="2013–2014"/></div>
    <div className="v7-two"><Section title="Dataset contract" subtitle="Declared inputs, outcome, evaluation design and explicit leakage exclusions.">
       <Detail name="Prediction task" value={workbench.data_contract.task}/>
       <Detail name="Target" value={workbench.data_contract.outcome}/>
       <Detail name="Evaluation design" value={workbench.data_contract.split}/>
       <p className="v11-fine">Excluded predictors: {workbench.data_contract.excluded_from_predictors.join(' · ')}</p>
     </Section>
     <Section title="Source quality control" subtitle="PHQ-9 responses cross-checked with original CDC DPQ fields.">
       {workbench.data_integrity?<><Detail name="Complete PHQ-9" value={fmt(workbench.data_integrity.phq9_observed_percent,2)+'%'}/>
       <Detail name="Normalized XPORT zero values" value={workbench.data_integrity.xport_zero_values_normalized.toLocaleString()}/>
       <Detail name="Raw/processed mismatches" value={workbench.data_integrity.source_check_mismatches}/>
       <p className="v11-fine">{workbench.data_integrity.reporting}</p></>:<p className="v11-fine">Data-quality results are retained locally for this case.</p>}
     </Section></div>
    <Section title="Complete feature inventory" subtitle="Every model input: measurement, type, valid observations, missingness, and distinct values.">
     <input className="v11-search" placeholder="Search variables…" value={search} onChange={(e:{target:{value:string}})=>setSearch(e.target.value)} aria-label="Search dataset variables"/>
     <Table head={['Variable','Data type','Observed','Missing %','Distinct values']} rows={profileList.map(x=>[x.label,x.type,x.observed,fmt(x.missing_pct,1)+'%',x.unique])}/>
    </Section>
    <div className="v7-two"><Section title="Variable distribution" subtitle="Real respondent counts in privacy-screened bins; sparse bins omitted.">
      <select className="v11-select" value={feature} onChange={(e:{target:{value:string}})=>setFeature(e.target.value)} aria-label="Choose variable">{workbench.features.map(f=><option key={f.feature} value={f.feature}>{f.label}</option>)}</select>
      <p className="v11-fine">{item.description}</p>
      <div className="v11-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={'distribution' in item?(item.distribution??[]):[]} margin={{top:8,right:8,left:0,bottom:20}}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="bin" tick={{fontSize:10}} angle={-15} textAnchor="end" height={60}/><YAxis/><Tooltip/><Bar dataKey="n" name="Respondents" fill="#278e82" radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></div>
      <Detail name="Observed responses" value={item.observed}/><Detail name="Missing responses" value={`${item.missing} (${fmt(item.missing_pct,1)}%)`}/>
      {item.type==='numeric'&&'summary' in item&&item.summary&&<Detail name="Median / interquartile range" value={`${item.summary.median} / ${item.summary.q25}–${item.summary.q75}`}/>}
     </Section>
     <Section title="Feature relationships" subtitle="Training-cohort Spearman correlations; associations are not causal effects.">
       <Table head={['Feature A','Feature B','Spearman ρ']} rows={workbench.correlations.slice(0,10).map(x=>[x.a,x.b,fmt(x.spearman_rho)])}/>
     </Section></div>
    <Section title="Cohort shift inspection" subtitle="Absolute standardized mean difference compares earlier and later survey cycles. This is an audit, not external-site validation.">
      <Table head={['Variable','|SMD|','Development missing','Evaluation missing']} rows={workbench.cohort_shift.map(x=>[x.feature,fmt(x.standardized_mean_difference),fmt(x.development_missing_pct,1)+'%',fmt(x.evaluation_missing_pct,1)+'%'])}/>
    </Section>
   </>}
   {stage==='Preprocessing'&&<>
    <div className="v11-pipeline"><div>Raw measurements</div><b>→</b><div>Training-only imputation</div><b>→</b><div>Scaling and encoding</div><b>→</b><div>{workbench.preprocessing.output_feature_count} model features</div></div>
    <Section title="Fitted transformation register" subtitle="Actual imputation and scaling values learned from training records only; never from the evaluation cohort.">
      <Table head={['Input variable','Fitted operation','Training missing','Validation missing','Post-imputation missing','Fill value']} rows={workbench.preprocessing.methods.map(x=>[x.label,x.method,x.training_missing,x.validation_missing,x.after_missing,String(x.impute_value)])}/>
     </Section>
    <div className="v7-two"><Section title="Before / after transformation" subtitle="Training quartiles; aggregate measurement examples, not individual patient records.">
      <select className="v11-select" value={feature} onChange={(e:{target:{value:string}})=>setFeature(e.target.value)}>{workbench.features.map(f=><option key={f.feature} value={f.feature}>{f.label}</option>)}</select>
      {prep&&'before_range' in prep&&prep.before_range&&'after_range' in prep&&prep.after_range?<>
        <Table head={['Quantile','Raw measurement','After preprocessing']} rows={([
         ['Q1',prep.before_range.q25,prep.after_range.q25],['Median',prep.before_range.median,prep.after_range.median],['Q3',prep.before_range.q75,prep.after_range.q75]
        ] as (string|number|null)[][]).map(row=>[String(row[0]),String(row[1]),String(row[2])])}/>
        <p className="v11-fine">Raw measurement units and standardized units differ; compare column-wise. Missing values are filled from the training median.</p>
       </>:<p className="v11-fine">Categorical inputs use training-mode imputation followed by one-hot encoding. Choose a numeric variable for quartile comparison.</p>}
     </Section>
     <Section title="Transformation properties" subtitle="These values are recorded from the fitted pipeline, not assumed defaults.">
       <Detail name="Original input features" value={workbench.preprocessing.input_feature_count}/>
       <Detail name="Transformed feature dimensions" value={workbench.preprocessing.output_feature_count}/>
       <Detail name="Missing after fitted imputation" value="0"/>
       {prep&&'center' in prep&&<><Detail name="Learned feature center" value={String(prep.center)}/><Detail name="Learned feature scale" value={String(prep.scale)}/></>}
       {prep&&'output_columns' in prep&&prep.output_columns&&<p className="v11-fine">Encoded categories: {prep.output_columns.join(' · ')}</p>}
       <p className="v11-fine">The evaluation cohort is transformed using training-fitted parameters. Median/mode estimation is repeated within every cross-validation fold.</p>
     </Section></div>
   </>}
   {stage==='Model selection'&&<>
    <div className="v11-metrics"><Metric label="Compared families" value={String(workbench.selection.candidates.length)} context="Includes dummy benchmark"/>
     <Metric label="Selection objective" value="Brier ↓" context="Validation probability error"/>
     <Metric label="Selected family" value={workbench.selection.model} context="Chosen before evaluation"/>
     <Metric label="Validation Brier" value={fmt(primary.validation.brier,4)} context="Selected model"/></div>
    <Section title="Candidate ranking" subtitle="Cross-validation tuning occurs within training data. Model family is selected using the separate validation cohort; later-cycle evaluation is not used for this choice.">
      <div className="v11-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={selectedModels}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="name" tick={{fontSize:11}}/><YAxis domain={['auto','auto']}/><Tooltip/><Bar dataKey="brier" name="Validation Brier (lower is better)" fill="#278e82" radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></div>
      <Table head={['Candidate','CV selection loss','Validation Brier','Validation ROC-AUC','Chosen']} rows={workbench.selection.candidates.map(x=>[x.name,x.cv_score===null?'Baseline':fmt(x.cv_score,4),fmt(x.validation.brier,4),fmt(x.validation.roc_auc,4),x.name===workbench.selection.model?'Selected':'—'])}/>
     </Section>
    <Section title="Learning-curve diagnostic" subtitle="Retrained with 25%, 50%, 75% and 100% of the training partition; measured against development validation only.">
      <div className="v11-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={workbench.selection.learning_curve}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="train_n" name="Training records"/><YAxis domain={['auto','auto']}/><Tooltip/><Legend/><Line dataKey="training_brier" name="Training Brier" stroke="#ba734e" strokeWidth={2}/><Line dataKey="validation_brier" name="Validation Brier" stroke="#278e82" strokeWidth={2}/></LineChart></ResponsiveContainer></div>
      <p className="v11-fine">The gap between training and validation error indicates generalization behavior. These curves are diagnostics, not evidence of an improved independent test score.</p>
    </Section>
    <Section title="Why this model?" subtitle="Explicit selection rule, not a visual ranking or choice based on the evaluation set.">
      <p className="v11-fine">The selected family minimizes validation Brier score among trained candidates. ROC-AUC describes discrimination; Brier measures probability accuracy. A lower score is better for Brier, while a higher ROC-AUC is better for discrimination. The dummy model is retained for baseline comparison.</p>
    </Section>
   </>}
   {stage==='Model mechanics'&&<>
    <div className="v11-pipeline"><div>Study variables</div><b>→</b><div>Fitted {workbench.preprocessing.output_feature_count}-column matrix</div><b>→</b><div>{workbench.selection.model}</div><b>→</b><div>Mortality event probability</div></div>
    <div className="v7-two"><Section title="Selected model configuration" subtitle="Hyperparameters from the best training-only cross-validation trial.">
       <Table head={['Hyperparameter','Selected value']} rows={Object.entries(primary.parameters).map(([k,v])=>[k,String(v)])}/>
     </Section><Section title="Feature relevance" subtitle="Validation-set permutation importance: performance loss when one predictor is shuffled.">
       <Table head={['Measurement','ROC-AUC decrease']} rows={workbench.selection.permutation_importance_validation.slice(0,12).map(x=>[x.feature,fmt(x.mean_metric_drop,4)])}/>
       <p className="v11-fine">Feature relevance is not causality or a treatment recommendation. Correlated predictors can share predictive information.</p>
     </Section></div>
   </>}
   {stage==='Enhancement'&&<>
    <div className="v11-metrics"><Metric label="Candidate method" value="Platt scaling" context="Logistic probability recalibration"/>
      <Metric label="Validation-only decision" value={pass?'Accepted':'Rejected'} context="Predeclared quality gate"/>
      <Metric label="OOF Brier gain" value={fmt(workbench.enhancement.rule.oof_brier_gain,4)} context="Positive means lower error"/>
      <Metric label="Minimum required gain" value={fmt(workbench.enhancement.rule.required_min_brier_gain,4)} context="Plus ROC-AUC noninferiority"/></div>
    <div className="v7-two"><Section title="Enhancement selection evidence" subtitle="Three-fold cross-fitted calibration on the development validation partition.">
       <Detail name="Original validation Brier" value={fmt(workbench.enhancement.rule.raw_validation_brier,4)}/>
       <Detail name="Calibrated OOF Brier" value={fmt(workbench.enhancement.rule.crossfit_calibrated_brier,4)}/>
       <Detail name="Original validation ROC-AUC" value={fmt(workbench.enhancement.rule.raw_validation_auc,4)}/>
       <Detail name="Calibrated OOF ROC-AUC" value={fmt(workbench.enhancement.rule.crossfit_calibrated_auc,4)}/>
       <p className="v11-fine">The enhancement decision was fixed using cross-fitted development-validation evidence before later-cycle evaluation. Rejection preserves the original model.</p>
      </Section>
      <Section title="Result of proposed enhancement" subtitle="Later-cycle evaluation is reported after the development-only decision.">
       <Table head={['Metric','Original model','Selected configuration']} rows={(['roc_auc','average_precision','brier','recall','precision','f1'] as const).map(k=>[k.replaceAll('_',' '),fmt(workbench.enhancement.later_cycle.original[k],4),fmt(workbench.enhancement.later_cycle.selected[k],4)])}/>
       <Detail name="Original operating threshold" value={fmt(workbench.enhancement.thresholds.original,3)}/>
       <Detail name="Selected operating threshold" value={fmt(workbench.enhancement.thresholds.selected,3)}/>
       <p className="v11-fine">No enhancement is adopted based on later-cycle outcomes; performance can improve or deteriorate.</p>
      </Section></div>
   </>}
   {stage==='Evaluation'&&<>
    <div className="v11-metrics"><Metric label="Later-cycle ROC-AUC" value={fmt(workbench.evaluation.metrics.roc_auc,4)} context="Discrimination"/>
      <Metric label="Brier score" value={fmt(workbench.evaluation.metrics.brier,4)} context="Probability error"/>
      <Metric label="Sensitivity" value={pct(workbench.evaluation.metrics.recall)} context="Detected events"/>
      <Metric label="Precision" value={pct(workbench.evaluation.metrics.precision)} context="Among positive classifications"/></div>
    <div className="v7-two"><Section title="Error decomposition" subtitle={`Validation-selected threshold ${fmt(workbench.evaluation.metrics.threshold,2)}; later-cycle counts.`}>
       <div className="v11-confusion"><div><b>{workbench.evaluation.metrics.confusion.tp}</b><span>True positives</span></div><div><b>{workbench.evaluation.metrics.confusion.fp}</b><span>False positives</span></div><div><b>{workbench.evaluation.metrics.confusion.fn}</b><span>False negatives</span></div><div><b>{workbench.evaluation.metrics.confusion.tn}</b><span>True negatives</span></div></div>
      </Section>
      <Section title="Reliability / calibration" subtitle="Predicted event frequency versus observed event frequency in evaluation bins.">
       <div className="v11-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={workbench.evaluation.calibration}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="bin"/><YAxis domain={[0,1]} tickFormatter={pct}/><Tooltip/><Legend/><Line type="monotone" dataKey="predicted" name="Predicted" stroke="#278e82" strokeWidth={2}/><Line type="monotone" dataKey="observed" name="Observed" stroke="#ba734e" strokeWidth={2}/></LineChart></ResponsiveContainer></div>
      </Section></div>
    <Section title="Subgroup performance inspection" subtitle="Age and sex strata with sufficient observed outcomes; descriptive only, not a guarantee of equitable performance.">
      <Table head={['Subgroup','N','Events','ROC-AUC','Recall','False positive rate','Brier']} rows={workbench.evaluation.subgroups.map(x=>[x.group,x.n,x.events,fmt(x.roc_auc),pct(x.recall),pct(x.false_positive_rate),fmt(x.brier)])}/>
     </Section>
    <Section title="Evaluation protocol" subtitle="Interpretation boundaries documented with the underlying experiment.">
      <div className="v7-checks">{workbench.methodology.limitations.map(x=><div key={x}><span>•</span><span>{x}</span></div>)}</div>
     </Section>
   </>}
  </div>;
}
