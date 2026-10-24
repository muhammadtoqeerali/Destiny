'use client';
import {useState, type CSSProperties, type KeyboardEvent} from 'react';
import {pct} from './fmt';

/* ------------------------------------------------------------------ */
/* Ranked model bars: one metric at a time, rows re-rank when it changes */
/* ------------------------------------------------------------------ */
export type RankRow = {name: string; sub?: string; selected?: boolean; baseline?: boolean; values: Record<string, number>};
export type RankMetric = {key: string; label: string; lowerIsBetter: boolean; domain: [number, number]; digits: number; note: string};

export function ModelRanking({rows, metrics, initial, label, tone}: {rows: RankRow[]; metrics: RankMetric[]; initial?: string; label: string; tone?: 'fiction'}) {
  const [key, setKey] = useState(initial ?? metrics[0].key);
  const m = metrics.find(x => x.key === key) ?? metrics[0];
  const order = rows.map((r, i) => i).sort((a, b) => {
    const d = rows[a].values[m.key] - rows[b].values[m.key];
    return m.lowerIsBetter ? d : -d;
  });
  const rankOf = (i: number) => order.indexOf(i);
  const span = m.domain[1] - m.domain[0];
  return (
    <div>
      <div className="fs-bars-head">
        <div className="fs-seg" role="radiogroup" aria-label={`${label}: metric`}>
          {metrics.map(x => (
            <button key={x.key} type="button" role="radio" aria-checked={x.key === m.key} onClick={() => setKey(x.key)}>{x.label}</button>
          ))}
        </div>
      </div>
      <p className="fs-axis-note" style={{marginBottom: '.8rem'}}>{m.note}</p>
      <ol className="fs-rank" data-tone={tone} aria-label={`${label}, ranked by ${m.label}`} style={{'--n': rows.length} as CSSProperties}>
        {rows.map((r, i) => {
          const v = r.values[m.key];
          const rank = rankOf(i);
          const width = Math.max(0, Math.min(1, (v - m.domain[0]) / span)) * 100;
          return (
            <li key={r.name} data-selected={r.selected ? '' : undefined} data-ref={r.baseline ? '' : undefined} style={{'--rank': rank} as CSSProperties}>
              <span className="fs-rank-name"><b>{r.name}</b>{r.sub && <small>{r.sub}</small>}</span>
              <span className="fs-rank-track" aria-hidden="true"><i style={{width: `${width}%`}} /></span>
              <span className="fs-rank-val">
                {v.toFixed(m.digits)}
                {r.selected ? <small>Selected</small> : rank === 0 && !r.baseline ? <small data-flag="best">{m.lowerIsBetter ? 'Lowest' : 'Highest'}</small> : null}
                <span className="fs-sr"> rank {rank + 1} of {rows.length}</span>
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Interval strip: a point estimate, optional interval, optional reference */
/* ------------------------------------------------------------------ */
export function IntervalStrip({title, value, digits = 3, lo, hi, domain, ticks, reference, note}: {
  title: string; value: number; digits?: number; lo?: number; hi?: number; domain: [number, number];
  ticks: {at: number; label: string}[]; reference?: {at: number; label: string}; note?: string;
}) {
  const at = (x: number) => `${((x - domain[0]) / (domain[1] - domain[0])) * 100}%`;
  const hasCi = lo !== undefined && hi !== undefined;
  return (
    <div className="fs-strip">
      <div className="fs-strip-head">
        <span>{title}</span>
        <b>{value.toFixed(digits)}</b>
      </div>
      <div className="fs-strip-track" role="img"
        aria-label={`${title} ${value.toFixed(digits)}${hasCi ? `, interval ${lo!.toFixed(digits)} to ${hi!.toFixed(digits)}` : ''}${reference ? `, ${reference.label} ${reference.at}` : ''}`}>
        {hasCi && <span className="fs-strip-ci" style={{left: at(lo!), width: `calc(${at(hi!)} - ${at(lo!)})`}} />}
        {reference && <span className="fs-strip-ref" style={{left: at(reference.at)}} />}
        <span className="fs-strip-pt" style={{left: at(value)}} />
      </div>
      <div className="fs-strip-ticks" aria-hidden="true">{ticks.map(t => <span key={t.label} style={{left: at(t.at)}}>{t.label}</span>)}</div>
      {note && <p className="fs-strip-note">{note}</p>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Reliability diagram: observed vs predicted, point area = people     */
/* ------------------------------------------------------------------ */
export type CalBand = {range: number[]; n: number; mean_predicted: number; observed_fraction: number};
const pointsText = (x: number) => `${Math.abs(x * 100).toFixed(1)} points`;

export function ReliabilityChart({bands}: {bands: CalBand[]}) {
  const gaps = bands.map(b => b.observed_fraction - b.mean_predicted);
  const [active, setActive] = useState(gaps.reduce((best, g, i) => (Math.abs(g) > Math.abs(gaps[best]) ? i : best), 0));
  const max = 0.6, x0 = 64, y0 = 352, size = 330;
  const sx = (v: number) => x0 + (v / max) * size;
  const sy = (v: number) => y0 - (v / max) * size;
  const maxN = Math.max(...bands.map(b => b.n));
  const radius = (n: number) => 9 + Math.sqrt(n / maxN) * 15;
  const ticks = [0, 0.2, 0.4, 0.6];
  const b = bands[active];
  const gap = gaps[active];
  const sentence = Math.abs(gap) < 0.01
    ? 'Observed and predicted frequencies are within one percentage point.'
    : gap > 0
      ? `People in this band reported difficulty ${pointsText(gap)} more often than the model predicted (under-prediction).`
      : `People in this band reported difficulty ${pointsText(gap)} less often than the model predicted (over-prediction).`;
  const onKey = (i: number) => (e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setActive(i); } };
  return (
    <div className="fs-cal">
      <svg viewBox="0 0 440 404" role="group" aria-label="Calibration chart: observed frequency against mean predicted probability for each reported band">
        {ticks.map(t => (
          <g key={t}>
            <line x1={x0} x2={x0 + size} y1={sy(t)} y2={sy(t)} stroke="#e3eaee" />
            <line y1={y0} y2={y0 - size} x1={sx(t)} x2={sx(t)} stroke="#e3eaee" />
            <text x={x0 - 10} y={sy(t) + 4} textAnchor="end">{Math.round(t * 100)}%</text>
            <text x={sx(t)} y={y0 + 20} textAnchor="middle">{Math.round(t * 100)}%</text>
          </g>
        ))}
        <text x={x0 + size / 2} y={y0 + 44} textAnchor="middle">Mean predicted probability</text>
        <text transform={`translate(14 ${y0 - size / 2}) rotate(-90)`} textAnchor="middle">Observed fraction reporting difficulty</text>
        <line x1={sx(0)} y1={sy(0)} x2={sx(max)} y2={sy(max)} stroke="#4f6478" strokeDasharray="5 5" strokeWidth="1.5" />
        {bands.map((band, i) => (
          <line key={`g${i}`} x1={sx(band.mean_predicted)} x2={sx(band.mean_predicted)} y1={sy(band.mean_predicted)} y2={sy(band.observed_fraction)} stroke="#8a5410" strokeWidth="2" strokeLinecap="round" opacity={active === i ? 1 : .45} />
        ))}
        {bands.map((band, i) => (
          <g key={i}>
            <circle className="fs-cal-pt" cx={sx(band.mean_predicted)} cy={sy(band.observed_fraction)} r={radius(band.n) + (active === i ? 3 : 0)}
              fill="#d48a22" fillOpacity={active === i ? .95 : .7} stroke="#fff" strokeWidth="2"
              tabIndex={0} role="button" aria-pressed={active === i}
              aria-label={`${pct(band.range[0], 0)} to ${pct(band.range[1], 0)} band, ${band.n} people, predicted ${pct(band.mean_predicted)}, observed ${pct(band.observed_fraction)}`}
              onClick={() => setActive(i)} onMouseEnter={() => setActive(i)} onFocus={() => setActive(i)} onKeyDown={onKey(i)} />
            <text x={sx(band.mean_predicted) + radius(band.n) + 13} y={sy(band.observed_fraction) + 4}>n = {band.n}</text>
          </g>
        ))}
      </svg>
      <div className="fs-cal-keys" aria-hidden="true">
        <span><i style={{background: '#d48a22'}} />Observed (point area = people in band)</span>
        <span><i style={{background: 'transparent', border: '1.5px dashed #4f6478'}} />Perfect calibration</span>
      </div>
      <div className="fs-cal-read" aria-live="polite">
        <div><span>Predicted band</span><b>{pct(b.range[0], 0)}–{pct(b.range[1], 0)}</b></div>
        <div><span>Predicted / observed</span><b>{pct(b.mean_predicted)} / {pct(b.observed_fraction)}</b></div>
        <div><span>People</span><b>{b.n}</b></div>
        <p>{sentence}</p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Permutation importance with spread across the five shuffles          */
/* ------------------------------------------------------------------ */
export function ImportanceBars({items}: {items: {name: string; value: number; std: number}[]}) {
  const lo = -0.008, hi = 0.022;
  const at = (x: number) => ((x - lo) / (hi - lo)) * 100;
  return (
    <div className="fs-imp" role="list" aria-label="Permutation importance, largest first">
      {items.map(it => {
        const weak = it.std >= it.value;
        return (
          <div className="fs-imp-row" role="listitem" key={it.name}
            aria-label={`${it.name}: Brier increase ${it.value.toFixed(4)}, spread ${it.std.toFixed(4)}${weak ? ', spread larger than the average increase' : ''}`}>
            <span>{it.name}</span>
            <span className="fs-imp-track" aria-hidden="true">
              <span className="fs-imp-zero" style={{left: `${at(0)}%`}} />
              <span className="fs-imp-bar" data-weak={weak ? '' : undefined} style={{left: `${at(0)}%`, width: `${at(it.value) - at(0)}%`}} />
              <span className="fs-imp-whisk" style={{left: `${at(it.value - it.std)}%`, width: `${at(it.value + it.std) - at(it.value - it.std)}%`}} />
            </span>
            <span className="fs-imp-val">{it.value.toFixed(4)}</span>
          </div>
        );
      })}
    </div>
  );
}
