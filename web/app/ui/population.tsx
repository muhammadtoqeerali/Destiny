import Link from 'next/link';
import type {CSSProperties} from 'react';
import mobility from '../data/real-mobility-summary-v49.json';
import {int, pct} from './fmt';

const survey = [
  {key: '2015-2016' as const, label: '2015–2016'},
  {key: '2017-2018' as const, label: '2017–2018'},
];

/** One dot per 1 in 100 respondents; the filled count is the rounded observed fraction. */
function Dots({filled, row}: {filled: number; row: number}) {
  return (
    <div className="fs-dots" aria-hidden="true" style={{'--row': row} as CSSProperties}>
      {Array.from({length: 100}, (_, i) => (
        <span key={i} className="fs-dot" data-on={i < filled ? '1' : '0'} style={{'--i': i} as CSSProperties} />
      ))}
    </div>
  );
}

export function PopulationHero() {
  return (
    <section className="fs-hero" aria-labelledby="doctor-title">
      <div className="fs-wrap fs-hero-grid">
        <div className="fs-hero-copy">
          <span className="fs-tag">Real public data, NHANES 2015–2018</span>
          <h1 className="fs-h1" id="doctor-title">About one in four older adults in these surveys reported trouble walking a quarter mile.</h1>
          <p className="fs-lede">
            US survey data on people aged 65 and over, what a machine-learning model can and cannot tell from eight health inputs,
            and fictional example profiles to explore.
          </p>
          <Link className="fs-link" href="/admin">See how the experiment was run <span aria-hidden="true">→</span></Link>
        </div>

        <figure className="fs-surface fs-picto" aria-label="Share of survey respondents who reported difficulty walking a quarter mile">
          {survey.map((s, row) => {
            const c = mobility.cohorts[s.key];
            return (
              <div className="fs-picto-row" key={s.key}>
                <div className="fs-picto-head">
                  <b>{pct(c.observed_event_fraction)}</b>
                  <span>{s.label}, {int(c.questionnaire_respondents)} respondents</span>
                </div>
                <Dots filled={Math.round(c.observed_event_fraction * 100)} row={row} />
              </div>
            );
          })}
          <figcaption className="fs-legend">
            <span><i style={{background: 'var(--amber)'}} />Reported difficulty</span>
            <span><i style={{background: '#dbe5e9'}} />No difficulty</span>
            <span className="fs-small">Each dot is 1 in 100. Unweighted counts from the analysed subset, not national prevalence.</span>
          </figcaption>
        </figure>
      </div>
    </section>
  );
}

export function ModelGlance() {
  const auc = mobility.evaluation.roc_auc;
  const outOf100 = Math.round(auc * 100);
  const sens = mobility.evaluation.sensitivity_at_0_5;
  return (
    <section className="fs-section" aria-labelledby="glance-title">
      <div className="fs-wrap">
        <div className="fs-section-head">
          <h2 className="fs-h2" id="glance-title">Can a model tell who reports difficulty?</h2>
        </div>
        <div className="fs-glance">
          <div>
            <p className="fs-bignum">{outOf100}<small>in 100</small></p>
            <p className="fs-lede" style={{marginTop: '.8rem'}}>
              Take one person who reported difficulty and one who did not. In about {outOf100} of 100 such pairs, the model gave the first person the higher score.
            </p>
            <div className="fs-pairbar" role="img" aria-label={`${outOf100} out of 100 pairs ranked correctly; 50 would be chance`}>
              <i style={{width: `${auc * 100}%`}} />
              <b style={{left: '50%'}} />
            </div>
            <div className="fs-pairbar-scale" aria-hidden="true">
              <span style={{left: '0%', transform: 'none'}}>0</span>
              <span style={{left: '50%'}}>50 = chance</span>
              <span style={{left: '100%', transform: 'translateX(-100%)'}}>100</span>
            </div>
            <p className="fs-small fs-muted" style={{marginTop: '.6rem'}}>This is the ROC-AUC ({auc.toFixed(3)}) on the 2017–2018 survey.</p>
          </div>

          <div className="fs-facts">
            <div className="fs-fact">
              <b>{pct(sens, 0)}</b>
              <span className="fs-muted">of people who reported difficulty scored above the default 0.5 cutoff. This is not a screening tool.</span>
            </div>
            <div className="fs-fact">
              <b>2017–18</b>
              <span className="fs-muted">was inspected while the model was being built, so this is an exploratory result rather than a fresh test.</span>
            </div>
            <div className="fs-fact">
              <b>8</b>
              <span className="fs-muted">inputs: age, sex, BMI, a mood score (PHQ-9) and four health histories.</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
