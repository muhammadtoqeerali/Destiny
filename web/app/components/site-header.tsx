'use client';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {BrandMark} from '../ui/brand';

const links = [
  {href: '/doctor', label: 'Doctor'},
  {href: '/admin', label: 'Research'},
];

export default function SiteHeader() {
  const path = usePathname() || '';
  return (
    <header className="fs-header">
      <div className="fs-wrap fs-header-in">
        <Link href="/doctor" className="fs-brand" aria-label="FrailtyScope home">
          <BrandMark />
          <span>FrailtyScope</span>
        </Link>
        <nav className="fs-nav" aria-label="Primary">
          {links.map(l => (
            <Link key={l.href} href={l.href} aria-current={path === l.href || path.startsWith(l.href + '/') ? 'page' : undefined}>
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
