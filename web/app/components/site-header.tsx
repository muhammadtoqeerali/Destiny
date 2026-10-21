'use client';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {HeartPulse, LockKeyhole, Stethoscope} from 'lucide-react';
export default function SiteHeader(){
 const inAdmin=usePathname().startsWith('/admin');
 return <header className="site-header"><div className="site-header-inner"><Link href="/doctor" className="site-brand" aria-label="FrailtyScope home"><span className="brand-mark"><HeartPulse size={22}/></span><span><b>FrailtyScope</b><small>AGEING & HEALTH INTELLIGENCE</small></span></Link><nav className="portal-nav" aria-label="Portal navigation"><Link href="/doctor" className={!inAdmin?'nav-active':''}><Stethoscope size={17}/> Doctor Portal</Link><Link href="/admin" className={inAdmin?'nav-active':''}><LockKeyhole size={17}/> Admin Portal</Link></nav><div className="header-status"><span className="live-dot"/> REAL PUBLIC-USE RESEARCH</div></div></header>;
}
