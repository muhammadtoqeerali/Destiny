'use client';
import {useState} from 'react';
import {CheckCircle2,ClipboardCheck,FileCheck2,LockKeyhole,ShieldAlert} from 'lucide-react';
import dossier from '../data/artifact-acceptance-v43.json';

type View='checks'|'fingerprints'|'outcomes';
/** No profile prop, fetch, patient input, binary loading, or clinical predictions. */
export function ArtifactAcceptanceV43(){
  const [view,setView]=useState<View>('checks');
  return <section className="v43-artifacts" aria-label="Synthetic artifact acceptance dossier">
    <header><div><span className="v43-kicker"><FileCheck2 size={17}/> MODEL ARTIFACT ACCEPTANCE · SOFTWARE REHEARSAL</span>
      <h3>Can a model bundle be trusted for serving?</h3>
      <p>We check the published <strong>fictional</strong> model metadata against its exact source checksum, feature ordering, preprocessing identity, and synthetic holdback receipt. This is not an approval to deploy a model trained on people.</p>
      </div><span className="v43-locked"><LockKeyhole size={16}/> Clinical promotion denied</span>
    </header>
    <div className="v43-summary"><div><b>{dossier.synthetic_registry_models}</b><span>fictional models verified</span></div>
      <div><b>{dossier.synthetic_input_features.length}</b><span>synthetic features matched</span></div>
      <div><b>{dossier.registered_clinical_models}</b><span>approved clinical models</span></div>
      <div><b>{dossier.clinical_outcomes.length}</b><span>clinical outcomes blocked</span></div></div>
    <div className="v43-tabs" role="group" aria-label="Artifact dossier view">
      <button type="button" aria-pressed={view==='checks'} onClick={()=>setView('checks')}>Acceptance checks</button>
      <button type="button" aria-pressed={view==='fingerprints'} onClick={()=>setView('fingerprints')}>Source fingerprints</button>
      <button type="button" aria-pressed={view==='outcomes'} onClick={()=>setView('outcomes')}>Four clinical gates</button>
    </div>
    {view==='checks'&&<div className="v43-checks" aria-label="Artifact acceptance check list">{dossier.checks.map(c=><article key={c.id}>
      <div><ClipboardCheck size={15}/><strong>{c.id.replaceAll('_',' ')}</strong><span>{c.status.replaceAll('_',' ')}</span></div>
      <p>{c.description}</p></article>)}</div>}
    {view==='fingerprints'&&<div className="v43-fingerprint" aria-label="Public synthetic source fingerprints">
      <p><CheckCircle2 size={16}/> Both checksums match public synthetic-only source receipts. No binary model file was read or validated.</p>
      <strong>Fictional model registry SHA256</strong><code>{dossier.model_registry_sha256}</code>
      <strong>Invented holdback receipt SHA256</strong><code>{dossier.validation_receipt_sha256}</code>
      <p>Preprocessing feature order: <b>{dossier.synthetic_input_features.join(' → ')}</b></p></div>}
    {view==='outcomes'&&<div className="v43-outcomes" aria-label="Clinical outcome promotion decisions">
      {dossier.clinical_outcomes.map(o=><article key={o.id}><h4>{o.name}</h4><strong>DENIED</strong>
       <ul>{o.missing.map(m=><li key={m}>{m}</li>)}</ul></article>)}</div>}
    <footer><ShieldAlert size={17}/><p>Metadata consistency is <strong>not independent clinical validation</strong>. Historical real-data fitting, clinical model loading, or patient risk estimation are unavailable. The existing clinical endpoint remains blocked.</p></footer>
  </section>;
}
