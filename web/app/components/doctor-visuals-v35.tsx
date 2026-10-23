'use client';

import {ArrowRight, CalendarDays, ClipboardList, HeartPulse, ShieldCheck, Users} from 'lucide-react';
import study from '../../public/data/nhanes-aggregate.json';

type Destination='Health profiles'|'Patient assessment'|'Visit history'|'Model evidence';
const total=study.counts.total;
const development=study.counts.development;
const later=study.counts.test;
const events=study.counts.test_events;
const share=(count:number)=>`${(count/total*100).toFixed(2)}%`;

/** Public-aggregate orientation only. No person-level records or model inference. */
export function DoctorHeroV35({onNavigate}:{onNavigate:(target:Destination)=>void}){
 return <header className="v35-hero" aria-label="Doctor Portal introduction">
   <div className="v35-hero-main">
     <div className="v35-hero-kicker"><HeartPulse size={17} aria-hidden="true"/> FRAILTYSCOPE / HEALTH RESEARCH</div>
     <h1>Clinical overview</h1>
     <p className="v35-hero-lede">Research evidence about ageing and physical function, presented with the clarity of a modern health service.</p>
     <p className="v35-hero-sub">Explore historical population findings, review de-identified measurements and understand what the available models can—and cannot—tell us.</p>
     <div className="v35-hero-actions">
       <button type="button" className="v35-action-primary" onClick={()=>onNavigate('Health profiles')}>
         Review health profiles <ArrowRight size={17} aria-hidden="true"/>
       </button>
       <button type="button" className="v35-action-secondary" onClick={()=>onNavigate('Patient assessment')}>
         Open assessment <ClipboardList size={17} aria-hidden="true"/>
       </button>
     </div>
     <div className="v35-hero-foot"><ShieldCheck size={16} aria-hidden="true"/> Independent research demonstration · no individual clinical predictions</div>
   </div>
   <div className="v35-hero-visual" aria-label="Published NHANES cohort overview">
     <div className="v35-insight-top"><span>HISTORICAL DATASET</span><CalendarDays size={18} aria-hidden="true"/></div>
     <div className="v35-insight-title">NHANES <span>2011–2014</span></div>
     <div className="v35-insight-total"><strong>{total.toLocaleString()}</strong><span>observations in the historical analysis sample</span></div>
     <div className="v35-cycle-meter" role="img" aria-label={`${development.toLocaleString()} development-cycle records and ${later.toLocaleString()} later-cycle records`}>
       <span style={{width:share(development)}}/><span style={{width:share(later)}}/>
     </div>
     <div className="v35-cycle-details"><div><i className="v35-key-develop"/><span>2011–2012<br/><b>{development.toLocaleString()} development</b></span></div><div><i className="v35-key-later"/><span>2013–2014<br/><b>{later.toLocaleString()} later-cycle</b></span></div></div>
     <div className="v35-insight-footer"><Users size={17} aria-hidden="true"/><span>Public historical aggregate counts · unweighted sample</span></div>
   </div>
 </header>;
}

export function CohortSnapshotV35(){
 return <section className="v35-cycle-story" aria-labelledby="v35-cycle-title">
   <div className="v35-cycle-copy"><span className="v35-overline">UNDERSTAND THE EVIDENCE</span><h2 id="v35-cycle-title">Two survey cycles, one historical benchmark</h2><p>The development and later-cycle groups contain different participants. The later survey cycle was previously inspected and does not provide a fresh independent validation.</p></div>
   <div className="v35-cycle-events"><div><span>Later-cycle observations</span><strong>{later.toLocaleString()}</strong></div><div><span>Recorded events</span><strong>{events.toLocaleString()}</strong></div><div className="v35-event-bar" role="img" aria-label={`${events} observed events and ${later-events} nonevents in the later-cycle subset`}><span style={{width:`${100*events/later}%`}}/></div><small>Unweighted descriptive counts · approximate five-year outcome</small></div>
 </section>;
}
