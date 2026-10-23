'use client';

import {useMemo,useState} from 'react';
import {BookOpen,CheckCircle2,ClipboardList,Info,LockKeyhole,Search,ShieldAlert} from 'lucide-react';
import evidence from '../data/model-translation-v42.json';

type Coverage='all'|'unmapped'|'partial';

/** Public candidate dictionary only: never accepts Patient Assessment state or sends values. */
export function ModelTranslationV42(){
  const [coverage,setCoverage]=useState<Coverage>('all');
  const [selected,setSelected]=useState('age');
  const shown=useMemo(()=>evidence.features.filter(f=>coverage==='all'||
    (coverage==='unmapped'?f.source_mapping_status==='UNMAPPED_IN_V24':
    f.source_mapping_status==='PARTIAL_SOURCE_VERIFIED_2011_2012')),[coverage]);
  const current=evidence.features.find(f=>f.id===selected)||evidence.features[0];
  return <section className="v42-crosswalk" aria-label="Public source-to-form crosswalk">
    <header className="v42-intro"><div><span className="v42-kicker"><BookOpen size={16} aria-hidden="true"/> PUBLIC RESEARCH TRANSLATION LEDGER</span>
      <h3>Where do Doctor assessment fields come from?</h3><p>Fourteen candidate survey-to-form links are documented. Only three have a partial source-verified v0.24 harmonization mapping; <strong>none has approved prediction-time use</strong>. Candidate source names are not deployable model inputs.</p>
    </div><span className="v42-lock"><LockKeyhole size={17} aria-hidden="true"/> Clinical model promotion denied</span></header>
    <div className="v42-metrics"><div><strong>{evidence.dictionary_candidate_coverage}</strong><span>candidate dictionary entries</span></div>
      <div><strong>{evidence.verified_harmonization_source_mappings}</strong><span>partial source-mapped in 2011–12</span></div>
      <div><strong>{evidence.unmapped_harmonization_features}</strong><span>unmapped in v0.24</span></div>
      <div><strong>{evidence.prediction_time_approvals}</strong><span>prediction-time approvals</span></div></div>
    <div className="v42-layout"><div className="v42-index"><div className="v42-filter" role="group" aria-label="Filter source mappings">
       <button type="button" aria-pressed={coverage==='all'} onClick={()=>setCoverage('all')}>All 14</button>
       <button type="button" aria-pressed={coverage==='unmapped'} onClick={()=>setCoverage('unmapped')}>11 unresolved</button>
       <button type="button" aria-pressed={coverage==='partial'} onClick={()=>setCoverage('partial')}>3 partial</button>
      </div><p className="v42-count"><Search size={14} aria-hidden="true"/> {shown.length} source dictionary entries shown</p>
      <div className="v42-field-list">{shown.map(f=><button type="button" key={f.id} className={current.id===f.id?'v42-active':''} aria-pressed={current.id===f.id} onClick={()=>setSelected(f.id)}>
        <span><strong>{f.form_label}</strong><small>{f.candidate_source_file} · {f.candidate_source_variables.join(', ')}</small></span><span className={f.source_mapping_status==='UNMAPPED_IN_V24'?'v42-tag missing':'v42-tag'}>{f.source_mapping_status==='UNMAPPED_IN_V24'?'Unmapped':'Partial'}</span>
      </button>)}</div></div>
      <div className="v42-detail" role="region" aria-label="Selected source mapping details"><span className="v42-kicker"><ClipboardList size={16} aria-hidden="true"/> SELECTED SOURCE CANDIDATE</span>
        <h4>{current.form_label}</h4>
        <dl><div><dt>Current Doctor input</dt><dd>{current.current_form_input}</dd></div>
          <div><dt>Documented candidate file</dt><dd><code>{current.candidate_source_file}</code></dd></div>
          <div><dt>Candidate survey variables</dt><dd><code>{current.candidate_source_variables.join(' · ')}</code></dd></div>
          <div><dt>Dictionary field type and unit</dt><dd>{current.dictionary_kind} · {current.dictionary_units}</dd></div>
          <div><dt>V0.24 source harmonization</dt><dd>{current.source_mapping_status==='UNMAPPED_IN_V24'?'Unresolved; codebook reference is not a verified transform.':'Partially source-verified in one historical wave; not approved for runtime.'}</dd></div></dl>
        <h5>What still needs review?</h5><ul>{current.review_gaps.map(t=><li key={t}><ShieldAlert size={15} aria-hidden="true"/>{t}</li>)}</ul>
        <p className="v42-caution"><Info size={17} aria-hidden="true"/> Prediction-time and source-to-form equivalence are <strong>unapproved for all 14 features</strong>. The live clinical API cannot use these links to calculate a patient risk.</p>
      </div></div>
    <details className="v42-outcomes"><summary>Four proposed clinical outcomes and their promotion gates</summary><div className="v42-outcome-grid">{evidence.outcome_promotion.map(o=><article key={o.id}>
       <strong>{o.name}</strong><span>NOT APPROVED</span><p>{o.current_status.replaceAll('_',' ').toLowerCase()}</p>
       <small>Artifact, preprocessing, prediction index, independent evaluation, calibration, governance and clinical-use approval are all pending.</small>
      </article>)}</div></details>
    <details className="v42-next"><summary>Required decisions before any real patient prediction</summary><ol>{evidence.scientific_next_actions.map(x=><li key={x}>{x}</li>)}</ol></details>
    <footer><CheckCircle2 size={17} aria-hidden="true"/><p>This page reads only existing public documentary source contracts. No private NHANES/HUNT data, fitted clinical models, patient fields, predictions or network submissions are used.</p></footer>
  </section>;
}
