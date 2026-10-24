'use client';
import {useId, useState, type ReactNode} from 'react';
import {Chevron} from './brand';

/** Smooth, keyboard-friendly reveal. Collapsed content is inert and hidden from assistive tech. */
export function Disclosure({label, meta, children, defaultOpen = false}: {label: string; meta?: string; children: ReactNode; defaultOpen?: boolean}) {
  const [open, setOpen] = useState(defaultOpen);
  const id = useId();
  return (
    <div className="fs-disc" data-open={open}>
      <button type="button" className="fs-disc-btn" aria-expanded={open} aria-controls={id} onClick={() => setOpen(o => !o)}>
        <span>{label}</span>
        {meta && <small>{meta}</small>}
        <Chevron />
      </button>
      <div className="fs-disc-panel" id={id} inert={!open}>
        <div className="fs-disc-inner"><div className="fs-disc-body">{children}</div></div>
      </div>
    </div>
  );
}
