'use client';

import {useState} from 'react';
import {Activity, ArrowRight, BarChart3, BookOpen, Check, CheckCircle2, ChevronRight,
  CircleHelp, ClipboardCheck, Database, Fingerprint, GitBranch, Layers3, LockKeyhole,
  Microscope, ScanLine, ShieldAlert, ShieldCheck, SlidersHorizontal, Sparkles, Workflow} from 'lucide-react';
import specialist from '../../public/data/nhanes-aggregate.json';
import refined from '../../public/data/nhanes-refinement.json';
import general from '../../public/data/nhanes-decision-quality-v12.json';

type View = 'overview'|'pipeline'|'models'|'assurance';
type Measure = 'auc'|'brier';
type Phase = {short:string;title:string;description:string;input:string;output:string;reference:string;checks:string[];limitation:string};
const phases:Phase[]=[
 {short:'Protocol',title:'Define a defensible research contract',description:'Validate study identity, endpoint, prediction index, feature availability and previous holdout use before an experiment can be considered.',input:'Source governance and timing documents',output:'Validated contract or a blocked route',reference:'v0.22–v0.24 · v0.29',checks:['Case identity and task preserved','Unapproved execution rejected','Holdout history cannot be reset'],limitation:'Original NHANES case remains blocked. Software checks do not authorize research.'},
 {short:'Harmonize',title:'Preserve the meaning of source variables',description:'Reviewed raw questionnaire codes can be mapped to canonical columns. Observed difficulty is kept distinct from structural skips and nonresponse.',input:'Invented source-coded PFQ records',output:'Canonical features and status fields',reference:'v0.24 · v0.29',checks:['Unexpected source fields rejected','Response status is explicit','No silent use of unmapped predictors'],limitation:'Only three of fourteen predictors are source-mapped in the NHANES contract.'},
 {short:'Partition',title:'Separate people before any fitting',description:'Generate repeatable, participant-disjoint development folds. Every candidate receives the same held-out group allocation.',input:'72 invented rows · 36 fictional people',output:'Three development folds',reference:'v0.25–v0.26 · v0.29',checks:['No person in train and validation','Stable common folds for candidates','Identifiers excluded from predictors'],limitation:'The diagram is schematic; it does not display actual per-person fold allocations.'},
 {short:'Preprocess',title:'Learn transformations on training folds only',description:'A fresh preprocessing pipeline is fitted inside each training partition. Missingness, status encoding and feature transformations are then applied to the corresponding validation partition.',input:'Canonical invented features and statuses',output:'Fold-consistent model inputs',reference:'v0.25 · v0.29',checks:['Train-only fitted statistics','Fresh pipeline per fold','Unrecognized fields rejected'],limitation:'Illustrated operations are not a fitted transformer being executed in your browser.'},
 {short:'Fit',title:'Evaluate registered synthetic model candidates',description:'The executable Python runner compares dummy-prior and logistic classifiers across the same three development folds and creates out-of-fold predictions in memory.',input:'Two pre-registered candidates',output:'Six synthetic fold-level fits',reference:'v0.26 · v0.29',checks:['Same fold assignments','Registered random seed','Reject nonfinite probabilities'],limitation:'No automatic winner is selected, no NHANES model is retrained, no model file is saved.'},
 {short:'Diagnose',title:'Inspect model reliability and error trade-offs',description:'Synthetic out-of-fold scores feed descriptive calibration, performance, cluster-conditional bootstrap and probability-shift stress diagnostics.',input:'Aligned invented OOF predictions',output:'Aggregate synthetic diagnostics',reference:'v0.28 · v0.29',checks:['OOF row/person alignment','Cluster-conditional intervals labeled','Row-level predictions discarded'],limitation:'Fixed-prediction uncertainty omits model refitting, model selection and survey design.'},
 {short:'Verify',title:'Prove a reproducible software execution',description:'The v0.30 test generates its own fictional fixture, repeats the Python workflow, checks matching aggregate hashes, and records a read-only-verifiable source lineage.',input:'Seed 1701 · approved source contracts',output:'Deterministic synthetic receipt',reference:'v0.30',checks:['Repeated aggregate hashes match','Source-chain digest verified','Immutable review never overwritten'],limitation:'Proves a tested software execution, not transportability or clinical validation.'},
];

const historical=[
 {name:'Specialist CatBoost',kind:'Historical specialist experiment',auc:specialist.testAtF2.roc_auc,brier:specialist.testAtF2.brier,threshold:specialist.threshold,recall:specialist.testAtF2.recall,precision:specialist.testAtF2.precision,fp:specialist.testAtF2.confusion.fp},
 {name:'Specialist histogram boosting',kind:'Historical optimized experiment',auc:refined.test.roc_auc,brier:refined.test.brier,threshold:refined.selectedThreshold,recall:refined.test.recall,precision:refined.test.precision,fp:refined.test.confusion.fp},
 {name:'General-purpose CatBoost',kind:'Historical general-case experiment',auc:general.evaluation.roc_auc,brier:general.evaluation.brier,threshold:general.locked_threshold,recall:general.evaluation.recall,precision:general.evaluation.precision,fp:general.evaluation.confusion.fp},
];
const SHA_SOURCE='85a346ced199a6f00b53232aec01cc3f99720e6a467ee0ab4db58631a0e458a1';
const SHA_SYNTHETIC='deb79398b4f62c49801b127c7a0e0f8cd045cf9dc61f3a7d87b140b9e5dab4b7';

function MiniFlow({active,onChoose}:{active:number;onChoose:(n:number)=>void}){
 return <div className="v33-flow" aria-label="Seven engineering stages">
   {phases.map((phase,index)=><button key={phase.short} type="button" className={index===active?'v33-node is-active':'v33-node'} onClick={()=>onChoose(index)} aria-current={index===active?'step':undefined}>
     <span className="v33-node-circle">{index===active?<Activity size={16}/>:String(index+1).padStart(2,'0')}</span><span className="v33-node-label">{phase.short}</span><ChevronRight className="v33-node-arrow" size={14}/>
   </button>)}
 </div>;
}

function FoldMatrix(){
 return <div className="v33-fold-matrix" role="img" aria-label="Conceptual person-disjoint three-fold cross-validation: two training groups and one validation group per fold">
  {Array.from({length:3},(_,fold)=><div className="v33-fold-row" key={fold}><b>Fold {fold+1}</b><div className="v33-fold-segments">{Array.from({length:3},(_,group)=><span key={group} className={fold===group?'is-validation':'is-training'}>{fold===group?'VALIDATE':'TRAIN'}</span>)}</div></div>)}
  <div className="v33-fold-legend"><span><i className="is-training"/>Training partition</span><span><i className="is-validation"/>Validation partition</span></div>
  <p>Conceptual group partition only. No participant IDs or per-row predictions are displayed.</p>
 </div>;
}

function ResearchLimit(){return <div className="v33-small-boundary" role="note"><ShieldAlert size={17}/><span>NHANES research fitting is <b>BLOCKED_FOR_NEW_ANALYSIS</b>. The index remains provisional, 11 predictors are unmapped, and the later cycle was previously inspected.</span></div>}

export function EngineStudioV33(){
 const [view,setView]=useState<View>('overview');
 const [active,setActive]=useState(2);
 const [measure,setMeasure]=useState<Measure>('auc');
 const [selected,setSelected]=useState(0);
 const [more,setMore]=useState(false);
 const stage=phases[active];
 const tabs:{id:View;label:string;sub:string}[]=[
   {id:'overview',label:'Mission control',sub:'Project at a glance'},
   {id:'pipeline',label:'Pipeline explorer',sub:'How the engine works'},
   {id:'models',label:'Model evidence',sub:'Historical evaluation'},
   {id:'assurance',label:'Quality & lineage',sub:'Trust boundaries'},
 ];
 const jump=(p:number)=>{setActive(p);setView('pipeline')};
 const chosen=historical[selected];
 const max=measure==='auc'?1:0.25;
 return <section className="v33-studio" aria-label="FrailtyScope research engineering studio">
   <header className="v33-hero">
    <div className="v33-hero-left"><div className="v33-eyebrow"><span className="v33-pulse"/> FRAILTYSCOPE ENGINEERING LAB <span>v0.33</span></div>
      <h2>Every experiment has<br/><em>a traceable story.</em></h2>
      <p>Explore the architecture behind the models—source contracts, preprocessing, cross-validation, historical evidence and reproducibility. The browser presents published aggregates and a documented synthetic workflow; it does not fit research models.</p>
      <div className="v33-hero-trust"><span><CheckCircle2 size={15}/> Software tests verified</span><span><Fingerprint size={15}/> Traceable synthetic receipt</span><span><ShieldCheck size={15}/> No person-level data</span></div>
    </div>
    <div className="v33-hero-right" aria-label="Engine architecture schematic">
      <div className="v33-orbit"><div className="v33-orbit-center"><Workflow size={30}/><strong>ENGINE</strong><small>7 STAGES</small></div><span className="v33-orbit-dot a"/><span className="v33-orbit-dot b"/><span className="v33-orbit-dot c"/></div>
      <div className="v33-hero-stat-row"><span><b>72</b> synthetic rows</span><span><b>36</b> fictional people</span><span><b>3</b> folds</span></div>
    </div>
   </header>
   <nav className="v33-nav" aria-label="Engine Studio views">{tabs.map(t=><button key={t.id} type="button" onClick={()=>setView(t.id)} aria-current={view===t.id?'page':undefined} className={view===t.id?'selected':''}><strong>{t.label}</strong><small>{t.sub}</small></button>)}</nav>

   {view==='overview'&&<div className="v33-view" aria-label="Mission control">
     <div className="v33-view-heading"><div><span className="v33-kicker">WORKFLOW OVERVIEW</span><h3>An auditable path from raw input to evidence.</h3><p>Select a stage to inspect what the engine actually validates.</p></div><button className="v33-text-action" type="button" onClick={()=>setView('pipeline')}>Explore pipeline <ArrowRight size={17}/></button></div>
     <MiniFlow active={active} onChoose={jump}/>
     <div className="v33-stat-grid">
       <div className="v33-stat-card"><Database size={20}/><span>Historical benchmark</span><strong>2,422</strong><small>NHANES observations · 2011–2014</small></div>
       <div className="v33-stat-card"><Layers3 size={20}/><span>Source mappings</span><strong>3 <i>/ 14</i></strong><small>Reviewed predictors for integration</small></div>
       <div className="v33-stat-card"><GitBranch size={20}/><span>Synthetic CV demonstration</span><strong>3</strong><small>Person-disjoint development folds</small></div>
       <div className="v33-stat-card"><ClipboardCheck size={20}/><span>Regression suite at v0.32</span><strong>708</strong><small>Passed · 1 skipped (workstation log)</small></div>
     </div>
     <div className="v33-summary-grid">
       <article className="v33-glass-panel"><div className="v33-panel-label"><Workflow size={16}/> CURRENT STAGE</div><div className="v33-panel-number">0{active+1} <span>/ 07</span></div><h4>{stage.title}</h4><p>{stage.description}</p><button type="button" className="v33-primary" onClick={()=>setView('pipeline')}>Inspect this stage <ArrowRight size={16}/></button></article>
       <article className="v33-white-panel"><span className="v33-panel-label"><ScanLine size={16}/> DEVELOPMENT VALIDATION</span><FoldMatrix/></article>
     </div>
     <ResearchLimit/>
   </div>}

   {view==='pipeline'&&<div className="v33-view" aria-label="Pipeline explorer">
     <div className="v33-view-heading"><div><span className="v33-kicker">INTERACTIVE SYSTEM MAP</span><h3>Seven engineering gates. One connected workflow.</h3><p>Inspect the inputs, transformations, safeguards and evidence for each stage.</p></div><div className="v33-count">{String(active+1).padStart(2,'0')} / 07</div></div>
     <MiniFlow active={active} onChoose={setActive}/>
     <div className="v33-workspace">
       <div className="v33-stage-detail"><span className="v33-kicker">STAGE {String(active+1).padStart(2,'0')} · IMPLEMENTATION</span><h4>{stage.title}</h4><p className="v33-stage-desc">{stage.description}</p>
         <div className="v33-io"><div><span><Database size={14}/> SOURCE / INPUT</span><strong>{stage.input}</strong></div><div className="v33-io-arrow"><ArrowRight size={20}/></div><div><span><Layers3 size={14}/> OUTPUT / EVIDENCE</span><strong>{stage.output}</strong></div></div>
         {active===2?<FoldMatrix/>:active===3?<div className="v33-preprocess"><div>Training people <span>FIT transformer</span></div><ArrowRight size={18}/><div>Validation people <span>TRANSFORM ONLY</span></div></div>:active===4?<div className="v33-fit-grid"><div><strong>dummy_prior</strong><small>Reference model</small></div><div><strong>logistic</strong><small>Registered candidate</small></div><div><strong>3 × 2 = 6</strong><small>synthetic fold fits</small></div></div>:active===6?<div className="v33-scan-line"><CheckCircle2 size={17}/> Two generated synthetic runs matched their aggregate SHA-256 digest.</div>:<div className="v33-scan-line"><CheckCircle2 size={17}/> Source and validation constraints are enforced in tested Python modules.</div>}
         <div className="v33-stage-controls"><button type="button" disabled={active===0} onClick={()=>setActive(Math.max(0,active-1))}>Previous</button><button className="v33-primary" type="button" disabled={active===6} onClick={()=>setActive(Math.min(6,active+1))}>Next gate <ArrowRight size={16}/></button></div>
       </div>
       <aside className="v33-evidence"><span className="v33-kicker">EVIDENCE CHECKLIST</span>{stage.checks.map(c=><div className="v33-check" key={c}><Check size={16}/><span>{c}</span></div>)}<div className="v33-proof"><small>IMPLEMENTATION SOURCE</small><b>{stage.reference}</b></div><div className="v33-caveat"><ShieldAlert size={18}/><span>{stage.limitation}</span></div></aside>
     </div>
     <div className="v33-note"><CircleHelp size={17}/> This browser does not run Python training. The verified synthetic execution occurred on the workstation and is documented by v0.30.</div>
   </div>}

   {view==='models'&&<div className="v33-view" aria-label="Historical model evidence">
      <div className="v33-view-heading"><div><span className="v33-kicker">HISTORICAL EVALUATION · PUBLISHED AGGREGATES</span><h3>Inspect results. Understand their provenance.</h3><p>Three different historical modeling protocols on the previously inspected later-cycle sample, shown without reranking or a new winner.</p></div><BarChart3 size={27}/></div>
      <div className="v33-model-layout"><div className="v33-white-panel"><div className="v33-chart-title"><h4>Published aggregate metric</h4><div className="v33-switch" role="group" aria-label="Metric"><button className={measure==='auc'?'is-selected':''} type="button" aria-pressed={measure==='auc'} onClick={()=>setMeasure('auc')}>ROC-AUC ↑</button><button className={measure==='brier'?'is-selected':''} type="button" aria-pressed={measure==='brier'} onClick={()=>setMeasure('brier')}>Brier ↓</button></div></div>
        <div className="v33-bar-plot" role="group" aria-label={`${measure==='auc'?'ROC-AUC':'Brier score'} interactive bars for three distinct historical experiments, starting at zero`}>{historical.map((h,i)=>{const value=h[measure];return <button key={h.name} type="button" className={selected===i?'v33-bar-row active':'v33-bar-row'} aria-label={`Inspect ${h.name}, ${measure} ${value.toFixed(4)}`} onClick={()=>setSelected(i)}><span>{h.name}</span><div className="v33-bar-track"><i style={{width:`${100*value/max}%`}}/></div><b>{value.toFixed(3)}</b></button>})}</div>
        <div className="v33-chart-axis"><span>0</span><span>{(max/2).toFixed(2)}</span><span>{max.toFixed(2)}</span></div><p className="v33-chart-foot">Each bar starts at zero. Comparisons are descriptive; protocols differ and no paired significance test is available.</p>
      </div>
      <aside className="v33-model-detail"><span className="v33-kicker">SELECTED HISTORICAL RECORD</span><h4>{chosen.name}</h4><p>{chosen.kind}</p><div className="v33-model-primary">{chosen.auc.toFixed(3)}<span>ROC-AUC</span></div><div className="v33-model-facts"><div><b>{chosen.brier.toFixed(3)}</b><span>Brier score</span></div><div><b>{chosen.threshold.toFixed(2)}</b><span>Threshold</span></div><div><b>{(chosen.recall*100).toFixed(1)}%</b><span>Sensitivity</span></div><div><b>{chosen.fp}</b><span>False-positive flags</span></div></div><span className="v33-model-label">Precision {(chosen.precision*100).toFixed(1)}%</span></aside></div>
      <div className="v33-study-bar"><div><span>2011–2012</span><b>1,165 development records</b></div><ArrowRight size={18}/><div><span>2013–2014</span><b>1,257 later-cycle records · 246 events</b></div></div>
      <ResearchLimit/>
   </div>}

   {view==='assurance'&&<div className="v33-view" aria-label="Quality and lineage">
      <div className="v33-view-heading"><div><span className="v33-kicker">REPRODUCIBILITY & GOVERNANCE</span><h3>Assurance is built into the workflow.</h3><p>Source boundaries, deterministic tests and audit provenance—not invented clinical-performance claims.</p></div><ShieldCheck size={29}/></div>
      <div className="v33-assurance-grid"><article className="v33-assurance-card"><GitBranch size={22}/><h4>Leakage protection</h4><p>Participant-disjoint development folds, training-only transformation fits, aligned out-of-fold records and validation guards.</p><span>Implemented in synthetic engine</span></article><article className="v33-assurance-card"><Fingerprint size={22}/><h4>Reproducible execution</h4><p>Fictional fixture generated internally; repeated execution uses a fixed seed and verifies aggregate digest equality.</p><span>v0.30 synthetic smoke passed</span></article><article className="v33-assurance-card"><ShieldCheck size={22}/><h4>Private-data boundary</h4><p>Only screened historical aggregates enter this webpage. Private participant rows, targets, fitted models and audits remain local.</p><span>Research execution still blocked</span></article></div>
      <div className="v33-lineage"><div><span className="v33-kicker">VERIFIED SYNTHETIC RECEIPT · v0.30</span><h4>Reproduce the evidence, not the claim.</h4><p>72 invented records · 36 fictional people · 3 folds · seed 1701 · repeated aggregate digest match</p></div><button className="v33-outline" type="button" aria-expanded={more} onClick={()=>setMore(!more)}>{more?'Hide':'Inspect'} fingerprints <ChevronRight size={15}/></button>{more&&<dl><dt>Source chain SHA-256</dt><dd>{SHA_SOURCE}</dd><dt>Synthetic aggregate SHA-256</dt><dd>{SHA_SYNTHETIC}</dd><dt>Scope</dt><dd>Fixed-seed synthetic development execution, not cross-study clinical validation</dd></dl>}</div>
      <div className="v33-readiness"><div><CheckCircle2 size={19}/><strong>Available</strong><span>Synthetic classification/regression workflows, leakage checks, reliability diagnostics</span></div><div><BookOpen size={19}/><strong>Prototype</strong><span>Survival and longitudinal specialist foundations</span></div><div><ShieldAlert size={19}/><strong>Not authorized</strong><span>New NHANES fitting, individual prognosis, fresh external-validation claims, HUNT execution</span></div></div>
   </div>}
   <footer className="v33-foot"><Microscope size={16}/><span>FrailtyScope · research engineering demonstration · historical aggregate reporting and documented synthetic execution only.</span></footer>
 </section>;
}
