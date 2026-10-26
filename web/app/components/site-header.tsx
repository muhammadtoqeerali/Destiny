'use client';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {BrainCircuit, HeartPulse, LockKeyhole, Stethoscope} from 'lucide-react';
export default function SiteHeader(){
 const path=usePathname(); const inAdmin=path.startsWith('/admin');
 return <header className="site-header"><div className="site-header-inner"><Link href="/interview" className="site-brand" aria-label="FrailtyScope home"><span className="brand-mark"><HeartPulse size={22}/></span><span><b>FrailtyScope</b><small>AGEING & HEALTH INTELLIGENCE</small></span></Link><nav className="portal-nav" aria-label="Portal navigation"><Link href="/interview" aria-label="Interview focus" className={path==='/interview'?'nav-active':''}><BrainCircuit size={17}/><span className="if-header-desktop">Interview focus</span><span className="if-header-mobile">Focus</span></Link><Link href="/doctor" className={path.startsWith('/doctor')?'nav-active':''}><Stethoscope size={17}/> Doctor Portal</Link><Link href="/admin" className={inAdmin?'nav-active':''}><LockKeyhole size={17}/> Admin Portal</Link></nav><div className="header-status"><span className="live-dot"/> HISTORICAL NHANES AGGREGATES</div></div></header>;
}
