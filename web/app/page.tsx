'use client';

import { useMemo, useState } from 'react';
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, BarChart3, BookOpenText,
  BrainCircuit, CheckCircle2, ChevronRight, CircleHelp, ClipboardList, Database,
  FileBarChart, FlaskConical, HeartPulse, LayoutDashboard, LockKeyhole, Menu,
  Search, ShieldCheck, SlidersHorizontal, Sparkles, Users, X
} from 'lucide-react';
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis
} from 'recharts';
import demo from '../public/data/demo.json';

type Screen = 'Overview' | 'Patients' | 'Model evaluation' | 'Data readiness' | 'Research notes';
type Patient = (typeof demo.patients)[number];
type RiskBand = 'All' | 'Lower' | 'Moderate' | 'Higher';

const nav: { name: Screen; icon: typeof LayoutDashboard }[] = [
  { name: 'Overview', icon: LayoutDashboard },
  { name: 'Patients', icon: Users },
  { name: 'Model evaluation', icon: BarChart3 },
  { name: 'Data readiness', icon: Database },
  { name: 'Research notes', icon: BookOpenText },
];

const tooltipStyle = { background: '#fff', border: '1px solid #e8edf0', borderRadius: 12,
  fontSize: 12, boxShadow: '0 12px 28px rgba(24, 51, 61, .1)' };

function Pill({ children, kind = 'neutral' }: { children: React.ReactNode; kind?: 'neutral' | 'teal' | 'amber' | 'red' }) {
  return <span className={`pill ${kind}`}>{children}</span>;
}
function RiskPill({ band }: { band: string }) {
  return <Pill kind={band === 'Higher' ? 'red' : band === 'Moderate' ? 'amber' : 'teal'}>
    <span className="status-dot" />{band} demo band
  </Pill>;
}
function MetricCard({ icon: Icon, title, value, foot, accent = 'blue' }: {
  icon: typeof Activity; title: string; value: string; foot: string; accent?: string;
}) {
  return <article className="metric-card">
    <div className="metric-top"><span className={`metric-icon ${accent}`}><Icon size={18}/></span><span className="metric-dots">···</span></div>
    <div className="metric-name">{title}</div><div className="metric-number">{value}</div>
    <div className="metric-foot">{foot}</div>
  </article>;
}
function RiskRing({ risk, size = 'large' }: { risk: number; size?: 'large' | 'small' }) {
  const color = risk >= 40 ? '#d8865c' : risk >= 20 ? '#d9aa53' : '#2c998b';
  return <div className={`risk-ring ${size}`} style={{ background: `conic-gradient(${color} ${risk}%, #e9eef0 ${risk}% 100%)` }}>
    <div className="risk-ring-inner"><strong>{risk.toFixed(1)}%</strong><span>demo estimate</span></div>
  </div>;
}
function SectionTitle({ kicker, title, details }: { kicker?: string; title: string; details?: string }) {
  return <div className="section-heading"><div>{kicker && <div className="eyebrow">{kicker}</div>}
    <h2>{title}</h2>{details && <p>{details}</p>}</div></div>;
}
function PatientPanel({ patient, showOpen, onOpen }: { patient: Patient; showOpen?: boolean; onOpen?: () => void }) {
  const priority = ['gait_speed_ms', 'sppb_score', 'grip_strength_kg', 'moca_score', 'medication_count', 'activity_minutes_day'];
  const vitals = priority.map(key => patient.features.find(f => f.key === key)).filter((x): x is Patient['features'][number] => Boolean(x));
  return <div className="patient-panel">
    <div className="panel-head"><div><div className="eyebrow">SIMULATED INDIVIDUAL</div><h3>{patient.id}</h3><p>{patient.age} years · {patient.sex}</p></div><RiskPill band={patient.band}/></div>
    <div className="risk-detail"><RiskRing risk={patient.risk}/><div className="risk-detail-copy"><h4>Illustrative 12-month fall event estimate</h4><p>Derived from an artificial outcome generator, not a validated clinical prediction.</p><div className="muted-text">{demo.summary.selectedModel}</div></div></div>
    <div className="subheading-row"><h4>Recorded indicators</h4><span>synthetic</span></div>
    <div className="vital-grid">{vitals.map(item => <div key={item.key} className="vital"><span>{item.name}</span><strong>{item.value}</strong></div>)}</div>
    <div className="subheading-row"><h4>Model response to individual features</h4><span>non-causal</span></div>
    <div className="explanation-list">
      {patient.explanations.slice(0, 4).map(item => <div className="explanation" key={item.key}>
        <div className={`explanation-arrow ${item.delta_pp >= 0 ? 'up' : 'down'}`}>
          {item.delta_pp >= 0 ? <ArrowUpRight size={17}/> : <ArrowDownRight size={17}/>}
        </div><div className="explanation-name"><strong>{item.name}</strong><span>{item.value}</span></div>
        <div className={`explanation-delta ${item.delta_pp >= 0 ? 'up' : 'down'}`}>
          {item.delta_pp > 0 ? '+' : ''}{item.delta_pp.toFixed(1)} pp
        </div>
      </div>)}
    </div>
    <p className="explanation-note">Differences in predicted probability when one feature is replaced by its synthetic cohort reference. Not additive, causal, or medical advice.</p>
    {showOpen && <button className="button primary full" onClick={onOpen}>Explore synthetic patient <ArrowRight size={16}/></button>}
  </div>;
}

export default function Home() {
  const [active, setActive] = useState<Screen>('Overview');
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<RiskBand>('All');
  const [selectedId, setSelectedId] = useState(demo.patients[0].id);
  const [mobileOpen, setMobileOpen] = useState(false);
  const patients = demo.patients;
  const selected = patients.find(p => p.id === selectedId) ?? patients[0];
  const displayed = useMemo(() => patients.filter(p =>
    (filter === 'All' || p.band === filter) &&
    (`${p.id} ${p.age} ${p.sex}`).toLowerCase().includes(query.toLowerCase())
  ), [patients, filter, query]);
  const changeScreen = (screen: Screen) => { setActive(screen); setMobileOpen(false); };
  const best = demo.summary.test;

  return <div className="app-shell">
    <aside className={`sidebar ${mobileOpen ? 'opened' : ''}`}>
      <div className="brand"><div className="brand-symbol"><HeartPulse size={23} strokeWidth={2.2}/></div>
        <div><div className="brand-name">FrailtyScope<span className="brand-star">.</span></div><div className="brand-desc">EXPLAINABLE AGEING & HEALTH</div></div>
        <button className="mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X size={20}/></button>
      </div>
      <div className="sidebar-label">WORKSPACE</div>
      <nav aria-label="Primary navigation" className="nav-list">{nav.map(item => <button key={item.name}
        onClick={() => changeScreen(item.name)} className={`nav-item ${active === item.name ? 'active' : ''}`}>
        <item.icon size={18}/><span>{item.name}</span>{active === item.name && <div className="nav-active-mark"/>}
      </button>)}</nav>
      <div className="sidebar-label sidebar-label-second">RESEARCH WORKSPACE</div>
      <div className="study-card"><div className="study-icon"><FlaskConical size={19}/></div><div className="study-title">Digi-FrailCare focus</div>
        <p>Data-driven approaches to understand frailty risk in older adults.</p>
        <div className="study-foot"><span className="study-indicator"/> Independent demonstration</div>
      </div>
      <div className="sidebar-bottom"><div className="data-safety"><ShieldCheck size={18}/><span><strong>Synthetic-only workspace</strong><small>No real patient data</small></span></div>
        <div className="side-version">Research prototype · v0.2.0</div></div>
    </aside>
    {mobileOpen && <button className="mobile-backdrop" aria-label="Close menu" onClick={() => setMobileOpen(false)}/>}
    <main className="main-area">
      <header className="topbar"><div className="topbar-left"><button className="mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={22}/></button>
        <span className="breadcrumb">Research workspace</span><ChevronRight size={14} className="breadcrumb-chev"/><strong>{active}</strong></div>
        <div className="topbar-right"><span className="topbar-protected"><LockKeyhole size={14}/> Public synthetic demo</span><span className="profile-chip">FS</span></div>
      </header>
      <div className="content">
        <div className="safety-strip"><span className="safety-icon"><FlaskConical size={16}/></span>
          <span><strong>Research demonstration:</strong> All individuals and outcomes are generated. Scores and findings are not derived from HUNT and are not suitable for patient care.</span>
          <span className="safety-label">SYNTHETIC DATA</span></div>
        {active === 'Overview' && <>
          <section className="welcome-section"><div><div className="eyebrow">RESEARCH OVERVIEW <span className="tiny-dot"/> PHASE 02</div>
            <h1>Making frailty risk <em>understandable.</em></h1><p>Explore a reproducible machine-learning demonstration designed around the questions behind digital care for older adults.</p></div>
            <button className="button outline" onClick={() => changeScreen('Research notes')}>View methodology <ArrowRight size={16}/></button></section>
          <div className="metric-grid">
            <MetricCard icon={Users} title="Synthetic participants" value={demo.summary.records.toLocaleString('en-US')} foot="Artificial records generated locally" accent="blue"/>
            <MetricCard icon={Activity} title="Artificial event rate" value={`${demo.summary.artificialEventRate}%`} foot="12-month synthetic event labels" accent="teal"/>
            <MetricCard icon={BrainCircuit} title="Test ROC-AUC" value={best.roc_auc.toFixed(3)} foot="Synthetic held-out evaluation" accent="purple"/>
            <MetricCard icon={ShieldCheck} title="Test Brier score" value={best.brier.toFixed(3)} foot="Lower is better · synthetic test" accent="orange"/>
          </div>
          <div className="overview-grid"><section className="surface chart-surface">
            <div className="surface-head"><div><div className="eyebrow">COHORT SIGNALS</div><h3>Illustrative risk distribution</h3><p>Held-out synthetic patients grouped by arbitrary demo bands</p></div><Pill>Test sample · n={demo.summary.testSize.toLocaleString()}</Pill></div>
            <div className="risk-legend"><span><i className="legend-dot low"/>Lower (&lt;20%)</span><span><i className="legend-dot med"/>Moderate (20–39.9%)</span><span><i className="legend-dot high"/>Higher (≥40%)</span></div>
            <div className="chart-container"><ResponsiveContainer width="100%" height="100%"><BarChart data={demo.riskDistribution} barSize={57} margin={{top:16,right:10,bottom:0,left:-20}}>
              <CartesianGrid vertical={false} stroke="#edf1f3" strokeDasharray="4 4"/><XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill:'#69808a',fontSize:12}}/>
              <YAxis axisLine={false} tickLine={false} tick={{fill:'#8a9ba2',fontSize:11}} allowDecimals={false}/>
              <Tooltip contentStyle={tooltipStyle}/><Bar dataKey="count" name="People" fill="#237e90" radius={[7,7,0,0]}/>
            </BarChart></ResponsiveContainer></div>
          </section>
          <section className="surface selected-surface"><div className="surface-head"><div><div className="eyebrow">CLINICIAN VIEW · MOCKUP</div><h3>Patient risk exploration</h3><p>One simulated profile from the test sample</p></div><button className="text-link" onClick={() => changeScreen('Patients')}>View all <ArrowRight size={15}/></button></div>
            <PatientPanel patient={patients[0]} showOpen onOpen={() => {setSelectedId(patients[0].id); changeScreen('Patients');}}/>
          </section></div>
          <div className="bottom-grid"><section className="surface compact-surface"><div className="surface-head"><div><div className="eyebrow">DATA COMPLETENESS</div><h3>Feature availability</h3><p>Simulated completeness; not HUNT measurements</p></div></div>
            <div className="coverage-list">{demo.coverage.map(item => <div key={item.name} className="coverage-row"><div className="coverage-text"><span>{item.name}</span><strong>{item.percent}%</strong></div>
              <div className="progress-rail"><div className="progress-fill" style={{width: `${item.percent}%`}}/></div></div>)}</div></section>
            <section className="surface compact-surface"><div className="surface-head"><div><div className="eyebrow">MODEL TRANSPARENCY</div><h3>Global feature sensitivity</h3><p>Test-set AUC drop when shuffled (synthetic)</p></div></div>
              <div className="signal-list">{demo.globalFeatures.slice(0, 5).map((item, idx) => <div key={item.key} className="signal-row"><span className="signal-rank">{String(idx+1).padStart(2,'0')}</span><span>{item.name}</span><div className="signal-track"><div style={{width:`${Math.max(7,item.importance / Math.max(.0001,demo.globalFeatures[0].importance)*100)}%`}}/></div></div>)}</div>
            </section></div>
        </>}
        {active === 'Patients' && <>
          <div className="page-heading"><div><div className="eyebrow">SIMULATED CASE LIBRARY</div><h1>Patient explorer</h1><p>Inspect generated example profiles and how model predictions respond to measured factors.</p></div><Pill kind="teal">90-or-fewer demo records</Pill></div>
          <div className="patients-layout"><section className="surface patients-directory"><div className="directory-head"><h3>Synthetic records</h3><span>{displayed.length} displayed</span></div>
            <div className="search-box"><Search size={17}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search ID, age, sex..." aria-label="Search synthetic records"/></div>
            <div className="filter-row">{(['All','Lower','Moderate','Higher'] as RiskBand[]).map(v => <button key={v} onClick={()=>setFilter(v)} className={`filter-button ${filter===v?'selected':''}`}>{v}</button>)}</div>
            <div className="patient-list">{displayed.length === 0 ? <p className="empty-state">No matching simulated records.</p> : displayed.map(patient =>
              <button key={patient.id} onClick={()=>setSelectedId(patient.id)} className={`patient-list-item ${patient.id===selected.id?'selected':''}`}>
                <span className="patient-initials">{patient.sex === 'Female' ? 'F' : 'M'}</span><span className="patient-list-text"><strong>{patient.id}</strong><small>{patient.age} years · {patient.sex}</small></span>
                <span className="patient-list-risk"><strong>{patient.risk.toFixed(1)}%</strong><ChevronRight size={15}/></span>
              </button>)}</div></section>
            <section className="surface patient-detail-surface"><PatientPanel patient={selected}/></section></div>
        </>}
        {active === 'Model evaluation' && <>
          <div className="page-heading"><div><div className="eyebrow">REPRODUCIBLE EXPERIMENT</div><h1>Model evaluation</h1><p>Results from one seeded synthetic patient-level experiment—not performance on HUNT.</p></div><Pill kind="teal"><CheckCircle2 size={14}/> Synthetic holdout</Pill></div>
          <div className="model-notice"><CircleHelp size={19}/><div><strong>How this model was chosen</strong><p>Three algorithms and two feature sets were compared on a separate validation set using Brier score. The selected model was then assessed on the untouched synthetic test sample. These metrics do not indicate real-world clinical utility.</p></div></div>
          <div className="metric-grid three"><MetricCard icon={BarChart3} title="ROC-AUC · test" value={best.roc_auc.toFixed(3)} foot="Artificial outcome discrimination"/><MetricCard icon={FileBarChart} title="Average precision · test" value={best.average_precision.toFixed(3)} foot="Depends on synthetic prevalence" accent="purple"/><MetricCard icon={ShieldCheck} title="Brier score · test" value={best.brier.toFixed(3)} foot="Squared probability error" accent="teal"/></div>
          <div className="model-grid"><section className="surface chart-surface"><div className="surface-head"><div><div className="eyebrow">RELIABILITY DIAGNOSTIC</div><h3>Calibration by risk bin</h3><p>Average predicted versus observed synthetic event frequency</p></div></div>
            <div className="chart-container"><ResponsiveContainer width="100%" height="100%"><LineChart data={demo.calibration} margin={{top:10,right:15,bottom:10,left:-12}}>
              <CartesianGrid stroke="#edf1f3" strokeDasharray="4 4"/><XAxis dataKey="predicted" type="number" domain={[0,1]} tickFormatter={v=>`${Math.round(v*100)}%`} tick={{fontSize:11,fill:'#80939b'}}/>
              <YAxis domain={[0,1]} tickFormatter={v=>`${Math.round(v*100)}%`} tick={{fontSize:11,fill:'#80939b'}}/>
              <Tooltip contentStyle={tooltipStyle} formatter={(v, name) => [typeof v==='number'?`${(v*100).toFixed(1)}%`:v,name]}/>
              <Line type="linear" dataKey="observed" stroke="#277e91" strokeWidth={3} dot={{r:5,fill:'#277e91'}} name="Observed rate"/>
              <Line type="linear" dataKey="predicted" stroke="#b6c2c7" strokeDasharray="5 5" strokeWidth={2} dot={false} name="Ideal calibration (diagonal)"/>
            </LineChart></ResponsiveContainer></div><p className="helper-note">Observed synthetic event rates should track the ideal 45° reference; groups are descriptive and may be sparse.</p></section>
            <section className="surface chart-surface"><div className="surface-head"><div><div className="eyebrow">CASE-MIX PROFILE</div><h3>Estimated risk by age group</h3><p>Mean synthetic probability, not published HUNT findings</p></div></div>
              <div className="chart-container"><ResponsiveContainer width="100%" height="100%"><BarChart data={demo.ageDistribution} margin={{top:14,right:15,bottom:5,left:-14}} barSize={49}>
                <CartesianGrid vertical={false} stroke="#edf1f3" strokeDasharray="4 4"/>
                <XAxis dataKey="group" axisLine={false} tickLine={false} tick={{fontSize:12,fill:'#69808a'}}/>
                <YAxis axisLine={false} tickLine={false} tick={{fontSize:11,fill:'#8a9ba2'}} unit="%"/>
                <Tooltip contentStyle={tooltipStyle}/><Bar dataKey="meanRisk" name="Mean risk (%)" fill="#65a9a9" radius={[7,7,0,0]}/>
              </BarChart></ResponsiveContainer></div><p className="helper-note">Risk estimates are generated by a model trained to learn an invented relationship.</p></section></div>
          <section className="surface evidence-panel"><div className="surface-head"><div><div className="eyebrow">UNCERTAINTY AND COMPARISON</div><h3>How reliable are these demonstration scores?</h3><p>Bootstrap intervals on the held-out synthetic test set, with a fixed selected model</p></div><Pill kind="teal">95% percentile intervals</Pill></div>
            <div className="evidence-grid"><div><small>Selected model</small><strong>{demo.summary.selectedModel}</strong><p>{demo.summary.selectedFeatures} input features · {demo.summary.featureGroup} set</p></div><div><small>ROC-AUC, test</small><strong>{demo.summary.test.roc_auc.toFixed(3)}</strong><p>95%: {demo.summary.testCI.roc_auc[0].toFixed(3)}–{demo.summary.testCI.roc_auc[1].toFixed(3)}</p></div><div><small>Brier score, test</small><strong>{demo.summary.test.brier.toFixed(3)}</strong><p>95%: {demo.summary.testCI.brier[0].toFixed(3)}–{demo.summary.testCI.brier[1].toFixed(3)}</p></div><div><small>Clinical-only LR</small><strong>{demo.summary.clinicalComparator.brier.toFixed(3)}</strong><p>Held-out Brier comparator; lower is better</p></div></div>
            <p className="helper-note">Intervals reflect variation in artificial test records, not model-development uncertainty, dataset shift, or confidence for actual patients.</p>
          </section>
          <section className="surface chart-surface decision-panel"><div className="surface-head"><div><div className="eyebrow">EXPLORATORY DECISION-CURVE ANALYSIS</div><h3>Net benefit across hypothetical thresholds</h3><p>Diagnostic demonstration against all / none policies; no threshold is clinically approved</p></div></div>
            <div className="chart-container"><ResponsiveContainer width="100%" height="100%"><LineChart data={demo.decisionCurve} margin={{top:12,right:12,bottom:8,left:2}}>
              <CartesianGrid stroke="#edf1f3" strokeDasharray="4 4"/><XAxis dataKey="threshold" unit="%" tick={{fontSize:11,fill:'#80939b'}}/>
              <YAxis tick={{fontSize:11,fill:'#80939b'}}/><Tooltip contentStyle={tooltipStyle}/><Legend/>
              <Line dataKey="model" stroke="#188f88" strokeWidth={3} dot={false} name="Selected model"/>
              <Line dataKey="all" stroke="#d3a15a" strokeWidth={2} dot={false} name="All positive"/>
              <Line dataKey="none" stroke="#9baab0" strokeWidth={2} dot={false} name="None positive"/>
            </LineChart></ResponsiveContainer></div>
          </section>
          <div className="surface results-table"><div className="surface-head"><div><div className="eyebrow">BENCHMARK</div><h3>Validation comparison</h3><p>Model selected using validation Brier score; no test-set selection</p></div></div>
            <div className="table-scroll"><table><thead><tr><th>Model · feature group</th><th>ROC-AUC</th><th>Average precision</th><th>Brier ↓</th><th>Selection</th></tr></thead><tbody>{demo.comparisons.map(m => <tr key={m.name}><td><strong>{m.name}</strong></td><td>{m.validation.roc_auc.toFixed(3)}</td><td>{m.validation.average_precision.toFixed(3)}</td><td>{m.validation.brier.toFixed(3)}</td><td>{m.name === demo.summary.selectedModel ? <Pill kind="teal">Selected</Pill> : 'Baseline'}</td></tr>)}</tbody></table></div>
          </div>
          <div className="surface results-table"><div className="surface-head"><div><div className="eyebrow">SUBGROUP CHECK</div><h3>Subgroup diagnostic · age & sex</h3><p>Exploratory group checks only. Small groups need interval estimates and external validation</p></div></div>
            <div className="table-scroll"><table><thead><tr><th>Group</th><th>Test participants</th><th>ROC-AUC</th><th>Brier ↓</th><th>Event rate</th></tr></thead><tbody>{demo.subgroups.map(g=><tr key={g.name}><td><strong>{g.name}</strong></td><td>{g.n}</td><td>{g.auc?.toFixed(3) ?? 'Not estimable'}</td><td>{g.brier.toFixed(3)}</td><td>{g.eventRate.toFixed(1)}%</td></tr>)}</tbody></table></div></div>
        </>}
        {active === 'Data readiness' && <>
          <div className="page-heading"><div><div className="eyebrow">DATA GOVERNANCE</div><h1>Data readiness & coverage</h1><p>Feature completeness in the simulated cohort; actual HUNT fields require an approved mapping and access.</p></div><Pill kind="amber">No HUNT records</Pill></div>
          <div className="surface data-readiness"><div className="surface-head"><div><div className="eyebrow">SYNTHETIC INPUT QUALITY</div><h3>Illustrative feature availability</h3><p>Missing values are imputed inside the train-fitted pipeline, not before splitting.</p></div></div>
            <div className="coverage-list">{demo.coverage.map(item=><div className="coverage-row" key={item.name}><div><strong>{item.name}</strong><span>{item.percent.toFixed(1)}% observed</span></div><div className="coverage-track"><div style={{width:`${item.percent}%`}}/></div></div>)}</div>
          </div>
          <div className="notes-grid" style={{marginTop:20}}><section className="surface notes-card"><span className="notes-icon"><ClipboardList size={22}/></span><h3>Research contract needed</h3><p>Person and encounter identifiers, baseline assessment dates, inclusion criteria, feature timing, true follow-up endpoints, outcome ascertainment and competing event dates must be documented before real-data fitting.</p><Pill kind="amber">Awaiting authorization</Pill></section>
          <section className="surface notes-card"><span className="notes-icon"><ShieldCheck size={22}/></span><h3>Publication-quality safeguards</h3><p>Pre-specify model selection, quantify missingness, reserve an untouched test set, evaluate calibration, use group/time aware splits and test domain shift before making any medical claims.</p><Pill kind="teal">Research workflow defined</Pill></section></div>
        </>}
        {active === 'Research notes' && <>
          <div className="page-heading"><div><div className="eyebrow">PROJECT TRANSPARENCY</div><h1>Research methods & provenance</h1><p>Clear boundaries between verified cohort metadata, synthetic prototyping, and future approved-data research.</p></div></div>
          <div className="notes-grid"><section className="surface notes-card"><span className="notes-icon"><Database size={21}/></span><h3>What is actually HUNT data?</h3><p>Nothing in this public dashboard. The variable *domains* were informed by published HUNT4 70+ descriptions, but all displayed participant records and labels are artificially generated.</p><Pill kind="teal">Data isolation enforced</Pill></section>
            <section className="surface notes-card"><span className="notes-icon"><BrainCircuit size={21}/></span><h3>What is the prediction target?</h3><p>An invented binary event representing a fall in the next 12 months. Neither future falls nor event timestamps have been retrieved from HUNT. No clinical validity is claimed.</p><Pill>Illustrative outcome only</Pill></section>
            <section className="surface notes-card"><span className="notes-icon"><SlidersHorizontal size={21}/></span><h3>What do patient explanations mean?</h3><p>For each input used by the selected model, the pipeline substitutes a synthetic development-set reference value and measures the resulting change in estimated risk. These differences are not SHAP or causal explanations.</p><Pill>Non-additive sensitivity</Pill></section>
            <section className="surface notes-card"><span className="notes-icon"><ShieldCheck size={21}/></span><h3>What happens with real HUNT data?</h3><p>Research ethics approval, HUNT DAC authorization, project agreement, and institutionally sanctioned secure computing are required. Restricted data must never be sent to the public demo or GitHub.</p><Pill kind="amber">Separate secure environment</Pill></section></div>
          <section className="surface roadmap"><div className="eyebrow">NEXT RESEARCH MILESTONES</div><h3>From software prototype to defensible science</h3>
            <div className="roadmap-steps"><div><span className="step-bubble">01</span><strong>Confirm endpoints and eligibility</strong><p>Define time-zero, follow-up, censoring, competing events and actual HUNT variable codes.</p></div><div><span className="step-bubble">02</span><strong>Build leakage-proof multimodal pipeline</strong><p>Temporal and group-aware evaluation, missingness, wearable selection and calibrated estimates.</p></div><div><span className="step-bubble">03</span><strong>Validate risk communication</strong><p>SHAP analysis, subgroup evaluation, uncertainty, decision curves and clinician co-design.</p></div></div>
          </section>
          <section className="surface references"><h3>Primary public references</h3><a href="https://www.ntnu.edu/digitalfrailcare" target="_blank" rel="noopener noreferrer">NTNU · Digi-FrailCare project <ArrowRight size={16}/></a>
            <a href="https://hunt-db.medisin.ntnu.no/hunt-db/" target="_blank" rel="noopener noreferrer">HUNT · Public variable databank <ArrowRight size={16}/></a>
            <a href="https://academic.oup.com/ije/article/55/2/dyag011/8490101" target="_blank" rel="noopener noreferrer">HUNT4 70+ · 2026 cohort profile <ArrowRight size={16}/></a>
            <a href="https://www.ntnu.edu/hunt/data" target="_blank" rel="noopener noreferrer">HUNT · Data access requirements <ArrowRight size={16}/></a>
            <a href="https://www.bmj.com/content/385/bmj-2023-078378" target="_blank" rel="noopener noreferrer">TRIPOD+AI · Reporting guidance <ArrowRight size={16}/></a>
          </section>
        </>}
        <footer className="footer"><span>© FrailtyScope — Independent ML research demonstration</span><span><FlaskConical size={14}/> Synthetic data only · Not for clinical use</span></footer>
      </div>
    </main>
  </div>;
}
