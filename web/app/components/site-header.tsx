'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { HeartPulse, LockKeyhole, Stethoscope } from 'lucide-react';
export default function SiteHeader(){
  const path=usePathname();
  const inAdmin=path.startsWith('/admin');
  return <header className="site-header"><div className="site-header-inner">
    <Link href="/doctor" className="site-brand" aria-label="FrailtyScope home"><span className="brand-mark"><HeartPulse size={22} strokeWidth={2.1}/></span><span><b>FrailtyScope</b><small>AGEING & HEALTH INTELLIGENCE</small></span></Link>
    <nav className="portal-nav" aria-label="Portal navigation">
      <Link href="/doctor" className={!inAdmin?'nav-active':''} aria-current={!inAdmin?'page':undefined}><Stethoscope size={17}/> Doctor Portal</Link>
      <Link href="/admin" className={inAdmin?'nav-active':''} aria-current={inAdmin?'page':undefined}><LockKeyhole size={17}/> Admin Portal</Link>
    </nav>
    <div className="header-status"><span className="live-dot"/> DEMO ENVIRONMENT</div>
  </div></header>;
}
