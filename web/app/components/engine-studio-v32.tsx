'use client';

import {useState} from 'react';
import {Activity, ArrowUpRight, CheckCircle2, Database, Fingerprint, GitBranch, LockKeyhole, ShieldCheck, Workflow} from 'lucide-react';
import historicalSpecialist from '../../public/data/nhanes-aggregate.json';
import historicalRefined from '../../public/data/nhanes-refinement.json';
import historicalGeneral from '../../public/data/nhanes-decision-quality-v12.json';

type Stage = {
  label: string;
  title: string;
  detail: string;
  inputs: string;
  proof: string;
  boundary: string;
  checks: string[];
};

/* Documentation of already-implemented synthetic capabilities, not a browser model runner.
   No participant data, predictions or fitted artifacts are loaded into the page. */
const stages:Stage[] = [
  {label:'Protocol', title:'Stop unsafe research before it starts',
   detail:'Case identity, outcome, predictor timing and holdout history are checked against the declared source contracts before any fold is fitted.',
   inputs:'v0.22–v0.29 source contracts',proof:'v0.30 source-chain hash + read-only private integrity verification',
   boundary:'NHANES is BLOCKED_FOR_NEW_ANALYSIS. A website demo cannot grant clearance.',
   checks:['Case identity and task unchanged','Prediction index remains provisional','Previously inspected holdout stays excluded']},
  {label:'Harmonize', title:'Preserve measurement meaning',
   detail:'The toy input maps fixed, source-reviewed mobility codes into canonical fields while preserving the distinction between observed difficulty, not performed, refusal and structural skip.',
   inputs:'Invented PFQ questionnaire rows',proof:'v0.24 contract + v0.29 synthetic integration tests',
   boundary:'Only 3 of 14 original NHANES predictors have reviewed mappings; the other 11 are not silently imputed.',
   checks:['Exact expected source columns','Explicit nonresponse and skip categories','Unexpected fields rejected']},
  {label:'Split', title:'Partition before fitting',
   detail:'The fictional 72-row, 36-person example uses three participant-disjoint development folds. Every candidate receives the same validation partitions.',
   inputs:'72 invented rows / 36 fictional people',proof:'v0.26 and v0.29 split and leakage regression tests',
   boundary:'Development out-of-fold assessment is not a new independent external test.',
   checks:['Zero participant overlap','Stable shared fold assignments','Outcome and record IDs excluded from features']},
  {label:'Preprocess', title:'Fit transformations using training rows only',
   detail:'Each fold creates a new fitted preprocessing pipeline for imputation and categorical representation. The validation fold is transformed with those training-only parameters.',
   inputs:'v0.25 exact canonical feature/status schema',proof:'v0.25 fold-safe preprocessing + v0.29 integrated test',
   boundary:'Missingness status and clinical semantics are not interchangeable.',
   checks:['Fresh pipeline on every fold','Training-fitted statistics only','Unexpected categories and invalid values guarded']},
  {label:'Fit models', title:'Compare registered toy candidates fairly',
   detail:'The real Python synthetic runner fits a dummy-prior reference and logistic model in each of three folds; it does not select a winner or replace the historic fitted Random Forest.',
   inputs:'Two registered synthetic classifiers × three folds',proof:'v0.29 end-to-end synthetic execution',
   boundary:'Six fictional fits, not six NHANES model fits. No saved fitted models.',
   checks:['Identical folds across candidates','Registered seeds and hyperparameters','Finite validation predictions required']},
  {label:'Reliability', title:'Measure what the development predictions support',
   detail:'Synthetic out-of-fold scores feed pooled error and discrimination diagnostics, descriptive calibration, paired fixed-prediction group bootstrap and toy probability-shift checks.',
   inputs:'Invented, aligned OOF records',proof:'v0.28 diagnostics integrated by v0.29',
   boundary:'Fixed-prediction bootstrap omits model retraining, selection uncertainty and survey design.',
   checks:['Row and subject alignment validated','Conditional intervals labeled honestly','No participant predictions exported']},
  {label:'Integrity', title:'Repeat the experiment, check the evidence',
   detail:'v0.30 generates its fictional fixture internally and repeats the entire synthetic workflow. Matching aggregate digests and source-contract fingerprints produce a reproducibility receipt.',
   inputs:'Synthetic seed 1701 and source contracts',proof:'v0.30 SHA-256 chain + repeated synthetic aggregate digest',
   boundary:'This proves deterministic execution within a tested environment, not a clinically validated prediction system.',
   checks:['Same synthetic aggregate digest twice','Immutable private review; verify is read-only','No data or fitted binary published']},
];

const history = [
  {name:'Specialist CatBoost',type:'Historical specialist experiment',auc:historicalSpecialist.testAtF2.roc_auc,brier:historicalSpecialist.testAtF2.brier,threshold:historicalSpecialist.threshold},
  {name:'Specialist histogram boosting',type:'Historical specialist experiment',auc:historicalRefined.test.roc_auc,brier:historicalRefined.test.brier,threshold:historicalRefined.selectedThreshold},
  {name:'General-purpose CatBoost',type:'Historical general case',auc:historicalGeneral.evaluation.roc_auc,brier:historicalGeneral.evaluation.brier,threshold:historicalGeneral.locked_threshold},
];

const chain = '85a346ced199a6f00b53232aec01cc3f99720e6a467ee0ab4db58631a0e458a1';
const receipt = 'deb79398b4f62c49801b127c7a0e0f8cd045cf9dc61f3a7d87b140b9e5dab4b7';

export function EngineStudioV32(){
 const [active,setActive]=useState(0);
 const [showProvenance,setShowProvenance]=useState(false);
 const stage=stages[active];
 return <section className="v32-studio" aria-label="FrailtyScope ML engine overview">
   <div className="v32-hero">
     <div className="v32-hero-copy">
       <span className="v32-eyebrow"><Workflow size={16}/> ENGINEERING WORKSPACE · v0.32 DEMO</span>
       <h2>From source evidence to trustworthy experiments.</h2>
       <p>Explore the implemented synthetic machine-learning workflow, its reproducibility safeguards and historical model evidence. This is a guided demonstration, not new data analysis or live clinical scoring.</p>
       <div className="v32-hero-pills"><span><CheckCircle2 size={15}/> Synthetic workflow tested</span><span><ShieldCheck size={15}/> Research access blocked</span><span><LockKeyhole size={15}/> No participant data in browser</span></div>
     </div>
     <div className="v32-metric-card" aria-label="Verified synthetic workflow metadata">
       <span>VERIFIED SYNTHETIC RECEIPT · v0.30</span>
       <strong>3 <small>development folds</small></strong>
       <div className="v32-mini-numbers"><div><b>72</b><span>invented rows</span></div><div><b>36</b><span>fictional people</span></div><div><b>6</b><span>toy model fits</span></div></div>
       <p>Seed 1701 · repeat execution verified</p>
     </div>
   </div>

   <div className="v32-section-heading"><div><span className="v32-overline">01 / WORKFLOW EXPLORER</span><h3>Inspect each engineering gate</h3><p>Choose a stage to see its inputs, safeguards and scientific limits.</p></div><span className="v32-step-count">{String(active+1).padStart(2,'0')} / {String(stages.length).padStart(2,'0')}</span></div>
   <div className="v32-stage-tabs" role="tablist" aria-label="ML workflow stages">
     {stages.map((s,i)=><button type="button" role="tab" id={`v32-stage-${i}`} aria-selected={active===i} aria-controls="v32-stage-panel"
       tabIndex={active===i?0:-1} className={active===i?'v32-stage active':'v32-stage'} key={s.label}
       onClick={()=>setActive(i)} onKeyDown={e=>{
         let next:number|undefined;
         if(e.key==='ArrowRight') next=(i+1)%stages.length;
         if(e.key==='ArrowLeft') next=(i+stages.length-1)%stages.length;
         if(e.key==='Home') next=0;
         if(e.key==='End') next=stages.length-1;
         if(next!==undefined){e.preventDefault();setActive(next);document.getElementById(`v32-stage-${next}`)?.focus();}
       }}>
       <span>{String(i+1).padStart(2,'0')}</span><strong>{s.label}</strong>
     </button>)}
   </div>
   <div className="v32-stage-panel" id="v32-stage-panel" role="tabpanel" aria-labelledby={`v32-stage-${active}`} tabIndex={0}>
     <div className="v32-stage-body">
       <span className="v32-overline">STAGE {active+1} · SYNTHETIC DEVELOPMENT</span>
       <h4>{stage.title}</h4><p>{stage.detail}</p>
       <div className="v32-fact-grid"><div><span>Input / contract</span><strong>{stage.inputs}</strong></div><div><span>Implementation evidence</span><strong>{stage.proof}</strong></div></div>
       <div className="v32-boundary"><ShieldCheck size={18}/><span><b>Research boundary</b>{stage.boundary}</span></div>
     </div>
     <div className="v32-check-list"><span className="v32-overline">VALIDATION CHECKS</span>{stage.checks.map(s=><div key={s}><CheckCircle2 size={17}/><span>{s}</span></div>)}
       <button type="button" className="v32-next" onClick={()=>setActive((active+1)%stages.length)}>Explore next stage <ArrowUpRight size={16}/></button>
     </div>
   </div>

   <div className="v32-two-col">
     <section className="v32-surface"><div className="v32-section-heading"><div><span className="v32-overline">02 / VALIDATION DESIGN</span><h3>Participant-disjoint development folds</h3></div><GitBranch size={23}/></div>
       <p>Illustrative arrangement for the 72-row / 36-person invented fixture. Each fold holds out a different group of fictional participants. The blocks below visualize the partition policy; they are not individual records.</p>
       <div className="v32-folds" aria-label="Three conceptual group-disjoint folds">
         {[0,1,2].map(i=><div className="v32-fold" key={i}><span>Fold {i+1}</span><div className="v32-fold-track">{[0,1,2].map(j=><span key={j} className={i===j?'holdout':'training'} title={i===j?'Validation':'Training'}/>)}</div><small>2 training partitions · 1 validation partition</small></div>)}
       </div>
       <div className="v32-legend"><span><i className="training"/> Training only</span><span><i className="holdout"/> Validation only</span></div>
     </section>
     <section className="v32-surface"><div className="v32-section-heading"><div><span className="v32-overline">03 / READINESS</span><h3>What is ready—and what is not</h3></div><Activity size={23}/></div>
       <div className="v32-readiness"><div><b>Implemented and tested</b><span>Synthetic classification/regression, fold-safe preprocessing, OOF reliability, source-integrity reviews</span></div><div><b>Educational prototypes</b><span>Survival and next-observed-visit longitudinal foundations</span></div><div><b>Protocol blocked</b><span>Original NHANES: provisional prediction index, 11 unmapped predictors, previously inspected later cycle</span></div></div>
     </section>
   </div>

   <section className="v32-surface v32-historical"><div className="v32-section-heading"><div><span className="v32-overline">04 / EXISTING RESEARCH · HISTORICAL AGGREGATES</span><h3>Three separate historical model experiments</h3><p>These fixed website values describe different model-building protocols. This is not a new leaderboard, paired comparison or independent validation.</p></div><Database size={23}/></div>
     <div className="v32-history-grid">{history.map(item=><div className="v32-history" key={item.name}><small>{item.type}</small><h4>{item.name}</h4><div><span>ROC-AUC <b>{item.auc.toFixed(3)}</b></span><span>Brier <b>{item.brier.toFixed(3)}</b></span></div><p>Historical selected threshold {item.threshold.toFixed(2)}</p></div>)}</div>
     <p className="v32-caption">The 2013–2014 survey cycle has been inspected repeatedly. Differences cannot establish a new best-performing model or generalization to Norwegian patients. Original historical aggregate JSON is unchanged.</p>
   </section>

   <section className="v32-surface v32-provenance"><div><span className="v32-overline"><Fingerprint size={15}/> 05 / REPRODUCIBILITY & PROVENANCE</span><h3>Every demonstrated result has a declared origin.</h3><p>v0.30 checked source-contract fingerprints and repeated synthetic aggregate outputs. The private integrity review remains on the authorized workstation.</p></div>
     <button type="button" className="v32-details-button" aria-expanded={showProvenance} onClick={()=>setShowProvenance(!showProvenance)}>{showProvenance?'Hide':'Show'} source fingerprints</button>
     {showProvenance&&<dl className="v32-fingerprints"><dt>Source-contract SHA-256</dt><dd>{chain}</dd><dt>Repeated synthetic aggregate SHA-256</dt><dd>{receipt}</dd><dt>Reproducibility seed</dt><dd>1701</dd><dt>Validation scope</dt><dd>Invented in-memory development rows only; no external/clinical evaluation</dd></dl>}
   </section>
   <div className="v32-footer"><ShieldCheck size={18}/><span>Interview demo only · no real-data reanalysis · no trained model downloaded · no individual risk score · no claim of Norwegian clinical validation.</span></div>
 </section>;
}
