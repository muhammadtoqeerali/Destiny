'use client';
import {useId, type ReactNode, type KeyboardEvent} from 'react';

/** Short explanation that opens on hover or keyboard focus and closes with Escape. */
export function InfoTip({label, children}: {label: string; children: ReactNode}) {
  const id = useId();
  const onKey = (e: KeyboardEvent<HTMLButtonElement>) => { if (e.key === 'Escape') e.currentTarget.blur(); };
  return (
    <span className="fs-tip">
      <button type="button" aria-label={label} aria-describedby={id} onKeyDown={onKey}>?</button>
      <span role="tooltip" id={id}>{children}</span>
    </span>
  );
}
