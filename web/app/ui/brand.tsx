/** FrailtyScope mark: a ring (the "scope") crossed by a stride trace. */
export function BrandMark({size = 30}: {size?: number}) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <circle cx="16" cy="16" r="14" fill="#0b7a82" />
      <circle cx="16" cy="16" r="10.2" fill="none" stroke="#ffffff" strokeOpacity=".28" strokeWidth="1.4" />
      <path d="M6.5 17.5h4.6l2.3-5.6 3.4 9.8 2.5-6.2 1.2 2h5" fill="none" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Chevron() {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path d="M5 7.5l5 5 5-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function InfoIcon({size = 18}: {size?: number}) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M10 9v5M10 6.2v.1" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}
