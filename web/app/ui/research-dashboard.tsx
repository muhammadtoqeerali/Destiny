'use client';
import {useRef, useState, type KeyboardEvent, type ReactNode} from 'react';
import mobility from '../data/real-mobility-summary-v49.json';
import demo from '../data/interview-benchmark-v47.json';
import historical from '../../public/data/nhanes-refinement.json';
import {Disclosure} from './disclosure';
import {InfoIcon} from './brand';
import {InfoTip} from './info-tip';
import {ImportanceBars, IntervalStrip, ModelRanking, ReliabilityChart, type RankMetric, type RankRow} from './charts';
import {fixed, int, pct, prettyFeature} from './fmt';

type Dataset = 'mobility' | 'fiction' | 'archive';
const datasets: {key: Dataset; label: string}[] = [
  {key: 'mobility', label: 'NHANES mobility 2015–2018'},
  {key: 'fiction', label: 'Fictional cohort'},
  {key: 'archive', label: 'Mortality archive'},
];

const stages = [
  {key: 'data', label: 'Data and preprocessing'},
  {key: 'models', label: 'Model selection'},
  {key: 'evaluation', label: 'Evaluation'},
  {key: 'drivers', label: 'What drives it'},
] as const;
type Stage = (typeof stages)[number]['key'];

const hyperLabel: Record<string, string> = {
  C: 'C', depth: 'depth', learning_rate: 'learning rate', max_depth: 'max depth', min_samples_leaf: 'min leaf size', max_leaf_nodes: 'max leaves',
};
const hyperText = (h: Partial<Record<string, number>>) => {
  const e = Object.entries(h).filter((kv): kv is [string, number] => typeof kv[1] === 'number');
  return e.length ? e.map(([k, v]) => `${hyperLabel[k] ?? k} ${v}`).join(', ') : 'Always predicts the training event rate';
};

/* ---------------- derived real-data values (never retyped) ---------------- */
const dev = mobility.cohorts['2015-2016'];
const later = mobility.cohorts['2017-2018'];
const selected = mobility.models.find(m => m.name === mobility.selected_model)!;
const logistic = mobility.models.find(m => m.name === 'Logistic regression')!;
const mobilityRows: RankRow[] = mobility.models.map(m => ({
  name: m.name, selected: m.name === mobility.selected_model, baseline: m.name === 'Dummy prior',
  values: {valBrier: m.validation_brier, cvBrier: m.cv_brier, valAuc: m.validation_auc},
}));
const mobilityMetrics: RankMetric[] = [
  {key: 'valBrier', label: 'Validation Brier', lowerIsBetter: true, domain: [0, 0.2], digits: 5, note: 'Brier score on the held-out development subset. Shorter bar = lower error = better. The selection rule uses this metric.'},
  {key: 'cvBrier', label: '3-fold CV Brier', lowerIsBetter: true, domain: [0, 0.2], digits: 5, note: 'Brier score averaged over three cross-validation folds of the training subset. Shorter bar = better.'},
  {key: 'valAuc', label: 'Validation ROC-AUC', lowerIsBetter: false, domain: [0.5, 0.8], digits: 5, note: 'Bars start at 0.5, which is chance. Longer bar = better at ranking people who reported difficulty above those who did not.'},
];

/* ---------------- panels for the real NHANES experiment ---------------- */
function DataPanel() {
  const fitShare = mobility.split.development_fit_n, selShare = mobility.split.development_selection_n;
  return (
    <div className="fs-panel-grid">
      <div className="fs-stack">
        <h2 className="fs-kicker">Two surveys, different people</h2>
        <div className="fs-flow">
          <div className="fs-flow-row">
            <div className="fs-flow-label"><b>2015–2016 (development)</b><span>{int(dev.questionnaire_respondents)} respondents</span></div>
            <div className="fs-flow-bar" style={{width: `${(dev.questionnaire_respondents / later.questionnaire_respondents) * 100}%`}}>
              <div className="fs-flow-fit" style={{flexGrow: fitShare}}>{fitShare}</div>
              <div className="fs-flow-sel" style={{flexGrow: selShare}}>{selShare}</div>
            </div>
            <div className="fs-small fs-muted">{fitShare} to fit models, {selShare} to choose between them</div>
          </div>
          <div className="fs-flow-row">
            <div className="fs-flow-label"><b>2017–2018 (later survey)</b><span>{int(later.questionnaire_respondents)} respondents</span></div>
            <div className="fs-flow-bar"><div className="fs-flow-test" style={{flexGrow: 1}}>{int(mobility.split.later_cycle_test_n)}</div></div>
            <div className="fs-small fs-muted">Used only to evaluate the selected model</div>
          </div>
        </div>
        <Disclosure label="Preprocessing steps" meta={`${mobility.preprocessing.length} steps`}>
          <ul className="fs-stack" style={{gap: '.55rem'}}>
            {mobility.preprocessing.map(s => <li key={s} className="fs-small">{s}</li>)}
          </ul>
          <p className="fs-small fs-muted">
            Complete nine-item PHQ-9 answers after the zero fix: {int(mobility.phq9_complete['2015-2016'])} (2015–2016) and {int(mobility.phq9_complete['2017-2018'])} (2017–2018).
            Refused or unknown answers are never recoded to zero.
          </p>
        </Disclosure>
      </div>

      <div className="fs-stack">
        <h2 className="fs-kicker">What the model classifies</h2>
        <div className="fs-def">
          <div><b>{int(dev.target_events)} of {int(dev.questionnaire_respondents)}</b><span>2015–2016 reported difficulty ({pct(dev.observed_event_fraction)})</span></div>
          <div><b>{int(later.target_events)} of {int(later.questionnaire_respondents)}</b><span>2017–2018 reported difficulty ({pct(later.observed_event_fraction)})</span></div>
        </div>
        <p className="fs-small fs-muted">
          Target: CDC item PFQ061B, current difficulty walking a quarter mile. Code 1 means no difficulty; codes 2–4 mean some, much difficulty or unable.
          People skipped by the PFQ054 routing or without an answer are excluded, never counted as “no difficulty”.
          Fractions are unweighted shares of the analysed subset.
        </p>
        <div>
          <p className="fs-small fs-muted" style={{marginBottom: '.5rem'}}>Eight inputs. Age is top-coded at 80+</p>
          <div className="fs-inputs">{mobility.predictors.map(f => <span key={f} className="fs-input-chip">{prettyFeature(f)}</span>)}</div>
        </div>
      </div>
    </div>
  );
}

function ModelsPanel() {
  const valGap = logistic.validation_brier - selected.validation_brier;
  return (
    <div className="fs-panel-grid">
      <div>
        <h2 className="fs-kicker" style={{marginBottom: '1rem'}}>Six candidates, one task, one split</h2>
        <ModelRanking rows={mobilityRows} metrics={mobilityMetrics} label="Candidate models" />
      </div>
      <div className="fs-stack">
        <div className="fs-callout">
          <b>Why {selected.name}?</b>
          <p>
            It has the lowest validation Brier ({fixed(selected.validation_brier, 5)}), {fixed(valGap, 5)} ahead of logistic regression ({fixed(logistic.validation_brier, 5)}).
          </p>
          <p className="fs-muted">
            Logistic regression did better in cross-validation ({fixed(logistic.cv_brier, 5)} against {fixed(selected.cv_brier, 5)}). Both differences are small, so {selected.name} is the selected model, not a proven best one.
          </p>
        </div>
        <Disclosure label="All numbers and settings">
          <div className="fs-table-wrap">
            <table className="fs-table">
              <caption className="fs-sr">Candidate models with cross-validation and validation scores</caption>
              <thead><tr><th>Model</th><th className="r">CV Brier</th><th className="r">Val. AUC</th><th className="r">Val. Brier</th><th>Settings</th></tr></thead>
              <tbody>
                {mobility.models.map(m => (
                  <tr key={m.name} data-selected={m.name === mobility.selected_model ? '' : undefined}>
                    <th scope="row">{m.name}</th><td className="r">{fixed(m.cv_brier, 5)}</td><td className="r">{fixed(m.validation_auc, 5)}</td><td className="r">{fixed(m.validation_brier, 5)}</td><td>{hyperText(m.hyperparameters)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="fs-small fs-muted">Rankings hold only within this dataset, target and split. No claim is made about other studies.</p>
        </Disclosure>
      </div>
    </div>
  );
}

function EvaluationPanel() {
  const ev = mobility.evaluation, ci = mobility.naive_row_bootstrap_95pct;
  return (
    <div className="fs-stack">
      <p className="fs-muted" style={{maxWidth: '70ch'}}>
        {selected.name} on the 2017–2018 survey: {int(ev.n)} people, {int(ev.events)} of whom reported difficulty. This survey was inspected during development, so these results are exploratory.
      </p>
      <div className="fs-panel-grid">
        <div className="fs-stack">
          <div className="fs-strips">
            <IntervalStrip title="ROC-AUC" value={ev.roc_auc} lo={ci.roc_auc[0]} hi={ci.roc_auc[1]} domain={[0.5, 1]}
              ticks={[{at: 0.5, label: '0.5 chance'}, {at: 0.75, label: '0.75'}, {at: 1, label: '1.0'}]}
              note={`Row-bootstrap 95% interval ${fixed(ci.roc_auc[0])}–${fixed(ci.roc_auc[1])}. Not adjusted for the NHANES survey design.`} />
            <IntervalStrip title="Brier score (lower is better)" value={ev.brier} digits={4} lo={ci.brier[0]} hi={ci.brier[1]} domain={[0, 0.25]}
              ticks={[{at: 0, label: '0'}, {at: 0.125, label: '0.125'}, {at: 0.25, label: '0.25'}]}
              note={`Row-bootstrap 95% interval ${fixed(ci.brier[0])}–${fixed(ci.brier[1])}.`} />
            <IntervalStrip title="Average precision" value={ev.average_precision} domain={[0, 1]}
              reference={{at: later.observed_event_fraction, label: 'event rate'}}
              ticks={[{at: 0, label: '0'}, {at: 0.5, label: '0.5'}, {at: 1, label: '1.0'}]}
              note={`Amber line: the ${pct(later.observed_event_fraction)} event rate, which is what random scoring would give.`} />
          </div>
          <Disclosure label="Cutoff and weighting details">
            <p className="fs-small">
              At the default 0.5 cutoff the model found <strong>{pct(ev.sensitivity_at_0_5)}</strong> of people who reported difficulty (sensitivity) and correctly left out <strong>{pct(ev.specificity_at_0_5)}</strong> of those who did not (specificity).
              The cutoff was not tuned or validated for any clinical use.
            </p>
            <p className="fs-small">
              Survey-weighted Brier score: {fixed(mobility.survey_weighted_brier_exploratory.brier)}, exploratory only. Survey-design variance was not estimated. Log loss: {fixed(ev.log_loss)}.
            </p>
          </Disclosure>
        </div>
        <div className="fs-stack">
          <h2 className="fs-kicker">Calibration</h2>
          <ReliabilityChart bands={mobility.calibration} />
          <p className="fs-small fs-muted">
            Three bands covering {int(mobility.calibration.reduce((a, b) => a + b.n, 0))} people are shown. {mobility.unshown_calibration_n} further people fall in bands too small to report (minimum 50 per band).
          </p>
        </div>
      </div>
    </div>
  );
}

function DriversPanel() {
  const items = mobility.permutation_importance.map(x => ({name: prettyFeature(x.feature), value: x.delta_brier, std: x.std}));
  const lim = mobility.limitations;
  return (
    <div className="fs-panel-grid">
      <div className="fs-stack">
        <h2 className="fs-kicker">
          Which inputs the model relies on
          <InfoTip label="About permutation importance">
            Each input is shuffled on the validation subset, and we record how much the Brier score worsens. A bigger increase means the model leans on that input more.
            This is reliance, not cause, and not an explanation for any one person.
          </InfoTip>
        </h2>
        <ImportanceBars items={items} />
        <p className="fs-small fs-muted">
          Bar: average increase in validation Brier. Whisker: ±1 standard deviation across five shuffles. Pale bars have a spread larger than their average, as for age and sex.
        </p>
      </div>
      <div className="fs-stack">
        <div className="fs-claims">
          <div>
            <h3>What this supports</h3>
            <ul>
              <li>A reproducible comparison of six models on public survey data.</li>
              <li>Which inputs the selected model relies on.</li>
              <li>An exploratory estimate of how it classifies current walking difficulty in a later survey.</li>
            </ul>
          </div>
          <div>
            <h3>What it does not</h3>
            <ul data-no="">
              <li>Predicting future frailty. The target is difficulty people have already reported.</li>
              <li>Clinical use, screening, or scores for real patients.</li>
              <li>Results for HUNT: no HUNT participant data were used.</li>
            </ul>
          </div>
        </div>
        <Disclosure label="All limitations" meta={`${lim.length + 1} items`}>
          <ul className="fs-stack" style={{gap: '.55rem'}}>
            {lim.map(l => <li key={l} className="fs-small">{l}.</li>)}
            <li className="fs-small">No model has been trained on HUNT or any other participant-level data.</li>
          </ul>
        </Disclosure>
      </div>
    </div>
  );
}

function MobilityView() {
  const [stage, setStage] = useState<Stage>('data');
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const idx = stages.findIndex(s => s.key === stage);
  const onKey = (e: KeyboardEvent) => {
    let n = idx;
    if (e.key === 'ArrowRight') n = (idx + 1) % stages.length;
    else if (e.key === 'ArrowLeft') n = (idx - 1 + stages.length) % stages.length;
    else if (e.key === 'Home') n = 0;
    else if (e.key === 'End') n = stages.length - 1;
    else return;
    e.preventDefault();
    setStage(stages[n].key);
    refs.current[n]?.focus();
  };
  return (
    <>
      <div className="fs-key" aria-label="Key figures">
        <div><span>Cohort</span><b>{int(dev.questionnaire_respondents + later.questionnaire_respondents)}</b><small>respondents aged 65+, from two surveys</small></div>
        <div><span>Selected model</span><b>{selected.name}</b><small>lowest validation Brier of six</small></div>
        <div><span>Validation Brier</span><b>{fixed(selected.validation_brier, 4)}</b><small>lower is better</small></div>
        <div><span>Later-survey ROC-AUC</span><b>{fixed(mobility.evaluation.roc_auc)}</b><small>exploratory, 2017–2018</small></div>
      </div>

      <div className="fs-stages" role="tablist" aria-label="Experiment stages" onKeyDown={onKey}>
        {stages.map((s, i) => (
          <button key={s.key} ref={el => { refs.current[i] = el; }} type="button" role="tab" id={`tab-${s.key}`} aria-selected={stage === s.key}
            aria-controls={`panel-${s.key}`} tabIndex={stage === s.key ? 0 : -1} className="fs-stage" onClick={() => setStage(s.key)}>
            <span className="fs-stage-n" aria-hidden="true">{i + 1}</span>{s.label}
          </button>
        ))}
      </div>
      <div key={stage} className="fs-panel" role="tabpanel" id={`panel-${stage}`} aria-labelledby={`tab-${stage}`}>
        {stage === 'data' && <DataPanel />}
        {stage === 'models' && <ModelsPanel />}
        {stage === 'evaluation' && <EvaluationPanel />}
        {stage === 'drivers' && <DriversPanel />}
      </div>
    </>
  );
}

/* ---------------- secondary datasets: compact and clearly separate ---------------- */
function FictionView() {
  const rows: RankRow[] = demo.models.map(m => ({
    name: m.name, selected: m.name === demo.selected_model, baseline: m.name === 'Dummy prior',
    values: {brier: m.validation.brier, auc: m.validation.roc_auc, ap: m.validation.average_precision},
  }));
  const metrics: RankMetric[] = [
    {key: 'brier', label: 'Validation Brier', lowerIsBetter: true, domain: [0, 0.2], digits: 4, note: 'Shorter bar = lower error = better.'},
    {key: 'auc', label: 'Validation ROC-AUC', lowerIsBetter: false, domain: [0.5, 0.8], digits: 4, note: 'Bars start at 0.5, which is chance.'},
  ];
  const c = demo.configuration;
  return (
    <div className="fs-aside-panel" style={{paddingTop: '1.6rem'}}>
      <div className="fs-trio">
        <div><span>Generated people</span><b>{int(c.generation_n)}</b><small>{int(c.train_n)} train, {int(c.validation_n)} validation, {int(c.test_n)} test</small></div>
        <div><span>Selected model</span><b>{demo.selected_model}</b><small>lowest validation Brier</small></div>
        <div><span>Synthetic test ROC-AUC</span><b>{fixed(demo.synthetic_test.roc_auc)}</b><small>Brier {fixed(demo.synthetic_test.brier)}</small></div>
      </div>
      <div className="fs-panel-grid">
        <div><h2 className="fs-kicker" style={{marginBottom: '1rem'}}>Model comparison on generated data</h2><ModelRanking rows={rows} metrics={metrics} label="Fictional cohort models" tone="fiction" /></div>
        <div className="fs-stack">
          <div className="fs-callout"><b>Purpose</b><p>Checks that the pipeline works end to end: group-safe splits, training-only preprocessing, selection on validation, a single test pass.</p><p className="fs-muted">Labels and measurements are invented, so these numbers say nothing about HUNT or any real population, and are not comparable with the NHANES results.</p></div>
          <Disclosure label="Calibration on the synthetic test set">
            <div className="fs-table-wrap"><table className="fs-table"><caption className="fs-sr">Synthetic calibration bands</caption>
              <thead><tr><th>Band</th><th className="r">People</th><th className="r">Predicted</th><th className="r">Observed</th></tr></thead>
              <tbody>{demo.calibration.map(b => <tr key={b.band}><th scope="row">{b.band}</th><td className="r">{b.count}{b.count < 20 ? ' (sparse)' : ''}</td><td className="r">{pct(b.mean_probability)}</td><td className="r">{pct(b.observed_fraction)}</td></tr>)}</tbody></table></div>
          </Disclosure>
        </div>
      </div>
    </div>
  );
}

function ArchiveView() {
  const h = historical;
  return (
    <div className="fs-aside-panel" style={{paddingTop: '1.6rem'}}>
      <div className="fs-trio">
        <div><span>Participants</span><b>{int(h.counts.total)}</b><small>NHANES 2011–2014, aged 65+</small></div>
        <div><span>Development</span><b>{int(h.counts.development)}</b><small>2011–2012</small></div>
        <div><span>Previously inspected</span><b>{int(h.counts.test)}</b><small>2013–2014</small></div>
      </div>
      <div className="fs-callout"><b>Kept for the record, closed to new analysis</b><p>An earlier case on approximately five-year all-cause mortality. Predictor mapping is unresolved and the later cycle was inspected before, so it is not independent validation. It does not predict diabetes, stroke or heart failure.</p></div>
      <div>
        <h2 className="fs-kicker" style={{marginBottom: '.8rem'}}>Historical validation-stage comparison</h2>
        <div className="fs-table-wrap"><table className="fs-table"><caption className="fs-sr">Historical mortality candidates</caption>
          <thead><tr><th>Candidate</th><th className="r">CV Brier</th><th className="r">AUC</th><th className="r">Brier</th></tr></thead>
          <tbody>{h.models.map(m => <tr key={m.name}><th scope="row">{m.name}</th><td className="r">{fixed(m.cv_brier, 4)}</td><td className="r">{fixed(m.auc, 3)}</td><td className="r">{fixed(m.brier, 4)}</td></tr>)}</tbody></table></div>
        <p className="fs-small fs-muted" style={{marginTop: '.8rem'}}>Do not compare these figures with the walking-difficulty results: the target, data and evaluation history differ.</p>
      </div>
    </div>
  );
}

const headings: Record<Dataset, {title: string; scope: string; tag: ReactNode}> = {
  mobility: {
    title: 'Classifying walking difficulty in older adults',
    scope: 'NHANES 2015–2018, adults 65 and over. The model classifies difficulty people have already reported walking a quarter mile. It does not predict future frailty.',
    tag: <span className="fs-tag">Real public data</span>,
  },
  fiction: {
    title: 'Fictional ageing cohort',
    scope: 'Generated people with invented outcomes, used to test the software. Not NHANES, not HUNT, not clinical.',
    tag: <span className="fs-tag" data-tone="fiction">Fictional</span>,
  },
  archive: {
    title: 'Mortality case, archived',
    scope: 'Approximately five-year all-cause mortality in NHANES 2011–2014. Blocked for new analysis.',
    tag: <span className="fs-tag" data-tone="archive">Archived</span>,
  },
};

export function ResearchDashboard({actions}: {actions?: ReactNode}) {
  const [ds, setDs] = useState<Dataset>('mobility');
  const h = headings[ds];
  return (
    <div className="fs-wrap">
      <header className="fs-rhead">
        <div className="fs-rhead-top">
          <div className="fs-seg" role="radiogroup" aria-label="Dataset">
            {datasets.map(d => <button key={d.key} type="button" role="radio" aria-checked={ds === d.key} onClick={() => setDs(d.key)}>{d.label}</button>)}
          </div>
          {actions}
        </div>
        <div style={{display: 'grid', gap: '.8rem', justifyItems: 'start'}}>
          {h.tag}
          <h1 className="fs-h1" style={{maxWidth: '24ch'}}>{h.title}</h1>
          <p className="fs-scope"><InfoIcon />{h.scope}</p>
        </div>
      </header>
      {ds === 'mobility' && <MobilityView />}
      {ds === 'fiction' && <FictionView />}
      {ds === 'archive' && <ArchiveView />}
    </div>
  );
}
