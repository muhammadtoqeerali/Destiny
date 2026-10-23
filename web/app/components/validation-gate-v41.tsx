'use client';
import {useState} from 'react';
import {ChartNoAxesCombined,ChevronDown,ClipboardCheck,LockKeyhole,ShieldCheck} from 'lucide-react';
import receipt from '../data/validation-readiness-v41.json';

/** Public documentary evidence only. Never takes props from Patient Assessment. */
export function ValidationGateV41(){
  const plans=receipt.scientific_readiness.outcome_plans;
  const [chosen,setChosen]=useState(plans[0].id);
  const selected=plans.find(p=>p.id===chosen)||plans[0];
  const checks=[
    ['Outcome and index definition',selected.target_definition_status],
    ['Baseline exclusion approved',selected.baseline_prevalence_exclusion_approved],
    ['Prediction horizon approved',selected.prediction_horizon_approved],
    ['Censoring and competing risks reviewed',selected.censoring_and_competing_risks_approved],
    ['Exact preprocessor registered',selected.validated_preprocessor_registered],
    ['Approved fitted clinical artifact',selected.fitted_clinical_artifact_registered],
    ['External calibration and validation',selected.external_validation_and_calibration_approved],
    ['Legal, ethics and secure workflow',selected.medical_use_and_data_access_approved],
  ] as const;
  return <section className="v41-panel" aria-label="Validation rehearsal and clinical approval gate">
    <div className="v41-heading"><div><span className="v41-eyebrow"><ClipboardCheck size={16} aria-hidden="true"/> VALIDATION & PROMOTION EVIDENCE</span><h3>Prove the workflow before predicting anyone&apos;s health</h3><p>Four real clinical outcomes remain unavailable. This section combines verified public research protocols with a separate software rehearsal on invented records. No patient assessment is used.</p></div><span className="v41-locked"><LockKeyhole size={16} aria-hidden="true"/> Clinical serving blocked</span></div>
    <div className="v41-numbers"><div><strong>3 / 14</strong><span>historically source-verified mappings in the partial v0.24 blueprint</span></div><div><strong>0 / 4</strong><span>clinical outcomes authorized for individual prediction</span></div><div><strong>240</strong><span>invented holdback records used to test synthetic classifiers</span></div></div>
    <div className="v41-subhead"><h4>Clinical readiness by outcome</h4><span>Documentary checks only · no clinical model loaded</span></div>
    <div className="v41-choices" role="group" aria-label="Select outcome for validation checklist">{plans.map(p=><button type="button" key={p.id} aria-pressed={p.id===chosen} className={p.id===chosen?'active':''} onClick={()=>setChosen(p.id)}>{p.name}</button>)}</div>
    <div className="v41-checks"><strong>{selected.name}</strong><p>No individual probability can be calculated. The following evidence has not been approved:</p><div>{checks.map(([label,value],i)=><div className="v41-check" key={label}><span><LockKeyhole size={14} aria-hidden="true"/> {label}</span><b>{i===0?String(value).replaceAll('_',' ').toLowerCase():value?'approved':'not approved'}</b></div>)}</div></div>
    <details className="v41-feature-details"><summary><ChevronDown size={17} aria-hidden="true"/> Review all 14 historical predictor mappings</summary><p>Source verification in the published 2011–2012 partial blueprint does <strong>not</strong> mean a predictor is approved for clinical runtime use. Prediction-time availability is unapproved for all 14.</p><div className="v41-feature-list">{receipt.scientific_readiness.features.map(f=><div key={f.feature}><strong>{f.feature.replaceAll('_',' ')}</strong><span>{f.public_mapping_status==='SOURCE_VERIFIED_PARTIAL_BLUEPRINT'?'Previously source-verified':'Unresolved in v0.24'}</span><small>Clinical timing unapproved</small></div>)}</div></details>
    <div className="v41-subhead"><h4><ChartNoAxesCombined size={17} aria-hidden="true"/> Test results from invented data only</h4><span>These are not metrics for NHANES patients or real diseases</span></div>
    <div className="v41-synthetic">{receipt.fictional_validation.metrics.map(m=><article key={m.id}><h5>{m.name}</h5><div><strong>{m.synthetic_auc.toFixed(3)}</strong><span>Synthetic ROC-AUC</span></div><div><strong>{m.brier.toFixed(3)}</strong><span>Synthetic Brier score</span></div><div><strong>{m.ece_5bins.toFixed(3)}</strong><span>5-bin calibration gap</span></div><small>{m.n} invented holdback cases · not externally validated</small></article>)}</div>
    <details className="v41-feature-details"><summary><ChevronDown size={17} aria-hidden="true"/> What the synthetic checks mean</summary><p>ROC-AUC measures ranking for invented class labels; Brier measures the average squared difference between an invented label and model probability; the calibration gap summarizes discrepancies in five bins. These checks verify evaluation software, not diagnostic accuracy or future illness forecasts.</p><p>These data came from the same fictional generator as model fitting. Bootstrap intervals describe artificial samples only and should never be interpreted as clinical uncertainty.</p></details>
    <footer className="v41-footer"><ShieldCheck size={18} aria-hidden="true"/> Reproducible public-only evidence. No clinical model binaries or patient details are read, stored, transmitted or scored here. The existing clinical inference endpoint remains disabled.</footer>
  </section>;
}
