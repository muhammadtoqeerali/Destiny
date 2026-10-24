'use client';
import {useRef, useState, type KeyboardEvent} from 'react';
import demo from '../data/interview-benchmark-v47.json';
import {Disclosure} from './disclosure';
import {InfoIcon} from './brand';
import {pct} from './fmt';

type Example = (typeof demo.fictional_examples)[number];
const people: Example[] = demo.fictional_examples;
const maxContribution = Math.max(...people.flatMap(p => p.illustrative_factors.map(f => Math.abs(f.log_odds_contribution))));
const factorName = (f: string) => { const s = f.replaceAll('_', ' '); return s.charAt(0).toUpperCase() + s.slice(1); };
const signed = (v: number) => (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(2);

function Measure({label, value, unit}: {label: string; value: number | null; unit?: string}) {
  return (
    <div className="fs-metric">
      <span>{label}</span>
      {value === null ? <b className="fs-na">Not recorded</b> : <b>{value}{unit && <small>{unit}</small>}</b>}
    </div>
  );
}

export function ProfileExplorer() {
  const [chosen, setChosen] = useState(0);
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const p = people[chosen];
  const score = p.fictional_model_probability;

  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const last = people.length - 1;
    let next = chosen;
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') next = chosen === last ? 0 : chosen + 1;
    else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') next = chosen === 0 ? last : chosen - 1;
    else if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = last;
    else return;
    e.preventDefault();
    setChosen(next);
    refs.current[next]?.focus();
  };

  return (
    <section className="fs-section" aria-labelledby="explorer-title">
      <div className="fs-wrap">
        <div className="fs-section-head">
          <h2 className="fs-h2" id="explorer-title">Explore a fictional profile</h2>
          <p className="fs-muted">Choose one of eight invented older adults. Nothing is entered, saved or sent anywhere.</p>
        </div>

        <div className="fs-fiction-note" role="note">
          <InfoIcon />
          <span><strong>Fictional example, not a patient.</strong> These profiles and their scores are generated. The score comes from a separate synthetic demo model, not from the NHANES model above.</span>
        </div>

        <div className="fs-surface fs-explorer">
          <div className="fs-rail" role="radiogroup" aria-label="Fictional example profiles" onKeyDown={onKey}>
            {people.map((x, i) => (
              <button
                key={x.id}
                ref={el => { refs.current[i] = el; }}
                type="button"
                role="radio"
                aria-checked={chosen === i}
                tabIndex={chosen === i ? 0 : -1}
                className="fs-person"
                onClick={() => setChosen(i)}
              >
                <span className="fs-avatar" aria-hidden="true">{x.age}</span>
                <span>
                  <strong>Example {i + 1}</strong>
                  <small>{x.sex}, {x.current_conditions.length} {x.current_conditions.length === 1 ? 'condition' : 'conditions'}</small>
                </span>
              </button>
            ))}
          </div>

          <div className="fs-work" aria-live="polite">
            <div key={p.id} className="fs-swap" style={{display: 'grid', gap: '1.4rem'}}>
              <div className="fs-snap-head">
                <div>
                  <h3>Example {chosen + 1}</h3>
                  <p className="fs-muted">{p.age} years old, {p.sex}</p>
                </div>
              </div>
              <div className="fs-metrics">
                <Measure label="Age" value={p.age} unit="yrs" />
                <Measure label="Daily-activity limits" value={p.adl_limitations} />
                <Measure label="Gait speed" value={p.gait_speed_mps} unit="m/s" />
                <Measure label="Grip strength" value={p.grip_strength_kg} unit="kg" />
              </div>
              <div>
                <p className="fs-small fs-muted" style={{marginBottom: '.5rem'}}>Reported conditions</p>
                <div className="fs-chips">
                  {p.current_conditions.length
                    ? p.current_conditions.map(c => <span className="fs-chip" key={c}>{c}</span>)
                    : <span className="fs-chip" data-empty>None in this profile</span>}
                </div>
              </div>
            </div>

            <div className="fs-score">
              <div className="fs-score-top">
                <div>
                  <span className="fs-tag" data-tone="fiction">Synthetic demo model</span>
                  <p className="fs-bignum" style={{marginTop: '.7rem'}}>{pct(score)}</p>
                </div>
                <p className="fs-muted fs-small" style={{maxWidth: '26ch'}}>Model score for invented follow-up decline in daily activities. It is not a risk for a real person.</p>
              </div>
              <div>
                <div className="fs-gauge" role="img" aria-label={`Synthetic model score ${pct(score)} on a scale from 0 to 100 percent`}>
                  <i style={{width: `${score * 100}%`}} />
                </div>
                <div className="fs-gauge-ticks" aria-hidden="true">
                  <span style={{left: '0%'}}>0%</span><span style={{left: '25%'}}>25%</span><span style={{left: '50%'}}>50%</span><span style={{left: '75%'}}>75%</span><span style={{left: '100%'}}>100%</span>
                </div>
              </div>
            </div>

            <div>
              <Disclosure label="What moved this score" meta={`${p.illustrative_factors.length} factors`}>
                <div className="fs-factors">
                  {p.illustrative_factors.map(f => {
                    const v = f.log_odds_contribution;
                    const w = (Math.abs(v) / maxContribution) * 50;
                    return (
                      <div className="fs-factor" key={f.feature}>
                        <span>{factorName(f.feature)}</span>
                        <div className="fs-factor-track" aria-hidden="true">
                          <i data-neg={v < 0 ? '' : undefined} style={{left: `${v >= 0 ? 50 : 50 - w}%`, width: `${w}%`}} />
                        </div>
                        <span className="fs-factor-val">{signed(v)}<small>{v >= 0 ? 'raises score' : 'lowers score'}</small></span>
                      </div>
                    );
                  })}
                </div>
                <p className="fs-small fs-muted">
                  Contributions to the log-odds of the synthetic logistic model, on the same scale for every profile. They describe the model, not causes.
                  In the invented data this profile’s follow-up was: <strong>{p.observed_demo_outcome === 1 ? 'decline' : 'no decline'}</strong>.
                </p>
              </Disclosure>
              <Disclosure label="How this demo model works">
                <div className="fs-steps" aria-label="Demo model pipeline">
                  <span className="fs-step">Ten measurements</span><span aria-hidden="true">→</span>
                  <span className="fs-step">Imputation and encoding fitted on training data only</span><span aria-hidden="true">→</span>
                  <span className="fs-step">{demo.selected_model}</span><span aria-hidden="true">→</span>
                  <span className="fs-step">Score</span>
                </div>
                <p className="fs-small fs-muted">Trained on 1,800 generated people with invented outcomes. It shows that the pipeline works; it says nothing about real older adults.</p>
              </Disclosure>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
