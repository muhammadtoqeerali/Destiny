'use client';
import { useMemo } from 'react';

export type ThresholdPoint = {
  threshold: number;
  recall: number;
  false_positive_rate: number;
  net_benefit: number;
  treat_all_net_benefit: number;
  treat_none_net_benefit: number;
};
type Mode = 'tradeoff' | 'benefit';
type Key = Exclude<keyof ThresholdPoint, 'threshold'>;

/** Responsive, dependency-free SVG: no hidden-tab ResizeObserver/recharts sizing. */
export function ThresholdSensitivityChart({data, selected, mode}: {
  data: ThresholdPoint[]; selected: number; mode: Mode;
}) {
  const plot = useMemo(() => {
    const keys: Key[] = mode === 'tradeoff'
      ? ['recall', 'false_positive_rate']
      : ['net_benefit', 'treat_all_net_benefit', 'treat_none_net_benefit'];
    const safe = data.length >= 2 && data.every(p =>
      [p.threshold, ...keys.map(key => p[key])].every(Number.isFinite));
    const unique = new Set(data.map(p => p.threshold)).size === data.length;
    if (!safe || !unique) return null;
    const sorted = [...data].sort((a, b) => a.threshold - b.threshold);
    const x0 = sorted[0].threshold;
    const x1 = sorted[sorted.length - 1].threshold;
    if (!(x1 > x0) || !Number.isFinite(selected) || selected < x0 || selected > x1) return null;
    const values = sorted.flatMap(p => keys.map(key => p[key]));
    const lo = mode === 'tradeoff' ? 0 : Math.min(0, ...values);
    const hi = mode === 'tradeoff' ? 1 : Math.max(0, ...values);
    const pad = mode === 'tradeoff' ? 0 : Math.max(0.035, (hi - lo) * 0.06);
    const minY = lo - pad, maxY = hi + pad;
    const w = 760, h = 305;
    const left = 70, right = 22, top = 24, bottom = 53;
    const px = (x: number) => left + (x - x0) / (x1 - x0) * (w - left - right);
    const py = (y: number) => top + (maxY - y) / (maxY - minY) * (h - top - bottom);
    const colors: Record<Key, string> = {
      recall: '#177d73', false_positive_rate: '#b45e37',
      net_benefit: '#177d73', treat_all_net_benefit: '#b45e37',
      treat_none_net_benefit: '#577c96',
    };
    const labels: Record<Key, string> = {
      recall: 'Event sensitivity', false_positive_rate: 'False-positive rate',
      net_benefit: 'Model net benefit', treat_all_net_benefit: 'Treat all',
      treat_none_net_benefit: 'Treat none',
    };
    const ticks = Array.from({length: 5}, (_, i) => minY + (maxY - minY) * i / 4);
    const lines = keys.map(key => ({key, label: labels[key], color: colors[key],
      d: sorted.map((p, i) => `${i === 0 ? 'M' : 'L'} ${px(p.threshold).toFixed(2)} ${py(p[key]).toFixed(2)}`).join(' '),
      value: sorted.find(p => Math.abs(p.threshold - selected) < 1e-8)?.[key],
    }));
    return {w, h, left, right, top, bottom, px, py, ticks, lines, minY, maxY, x0, x1};
  }, [data, mode, selected]);

  if (!plot) {
    return <p role="alert" className="v11-fine">Threshold chart unavailable: invalid or incomplete aggregate data. No values have been estimated.</p>;
  }
  const xTicks = [plot.x0, plot.x0 + (plot.x1 - plot.x0) / 4,
    plot.x0 + (plot.x1 - plot.x0) / 2, plot.x0 + 3 * (plot.x1 - plot.x0) / 4, plot.x1];
  return <div style={{width: '100%', minWidth: 0}}>
    <svg role="img" aria-label={`${mode === 'tradeoff' ? 'Sensitivity and false-positive rate' : 'Net benefit'} by threshold. Selected threshold ${selected.toFixed(2)}.`}
      viewBox={`0 0 ${plot.w} ${plot.h}`} preserveAspectRatio="xMidYMid meet"
      style={{display: 'block', width: '100%', height: 'auto', minHeight: 240}}>
      <rect x="0" y="0" width={plot.w} height={plot.h} fill="transparent"/>
      {plot.ticks.map((t, i) => <g key={i}>
        <line x1={plot.left} x2={plot.w - plot.right} y1={plot.py(t)} y2={plot.py(t)} stroke="#e4ecea" strokeDasharray="4 4" />
        <text x={plot.left - 12} y={plot.py(t) + 4} fontSize="12" textAnchor="end" fill="#53767c">{mode === 'tradeoff' ? `${Math.round(t * 100)}%` : t.toFixed(2)}</text>
      </g>)}
      <line x1={plot.left} x2={plot.left} y1={plot.top} y2={plot.h - plot.bottom} stroke="#819c9d" />
      <line x1={plot.left} x2={plot.w - plot.right} y1={plot.h - plot.bottom} y2={plot.h - plot.bottom} stroke="#819c9d" />
      {xTicks.map((t, i) => <text key={i} x={plot.px(t)} y={plot.h - plot.bottom + 23} textAnchor="middle" fontSize="12" fill="#53767c">{t.toFixed(2)}</text>)}
      <text x={plot.w / 2} y={plot.h - 10} fontSize="12" textAnchor="middle" fill="#53767c">Probability threshold</text>
      {plot.lines.map(line => <path key={line.key} d={line.d} stroke={line.color} strokeWidth="3" strokeLinejoin="round" fill="none"
        strokeDasharray={line.key === 'treat_none_net_benefit' ? '6 5' : undefined} />)}
      <line x1={plot.px(selected)} x2={plot.px(selected)} y1={plot.top} y2={plot.h - plot.bottom}
        stroke="#303f49" strokeDasharray="3 5" strokeWidth="1.8" />
      {plot.lines.filter(line => line.value !== undefined).map(line => <circle key={line.key}
        cx={plot.px(selected)} cy={plot.py(line.value!)} r="5" fill={line.color} stroke="white" strokeWidth="2"/>)}
      <text x={Math.min(plot.px(selected) + 6, plot.w - 88)} y={plot.top - 6} fontSize="11" fill="#303f49">Selected {selected.toFixed(2)}</text>
    </svg>
    <div aria-label="Chart legend" style={{display: 'flex', flexWrap: 'wrap', gap: 16, justifyContent: 'center', fontSize: 12, color: '#476e72'}}>
      {plot.lines.map(line => <span key={line.key} style={{display: 'inline-flex', gap: 6, alignItems: 'center'}}>
        <span aria-hidden="true" style={{width: 17, height: 3, background: line.color, display: 'inline-block'}}/>
        {line.label}{line.value === undefined ? '' : `: ${mode === 'tradeoff' ? (line.value * 100).toFixed(1) + '%' : line.value.toFixed(3)}`}
      </span>)}
    </div>
  </div>;
}
