'use client';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {HeartPulse,Stethoscope,BarChart3} from 'lucide-react';
export default function SiteHeader(){
 const path=usePathname();const research=path.startsWith('/admin');
 return <header className="site-header"><div className="site-header-inner"><Link href="/doctor" className="site-brand" aria-label="FrailtyScope home"><span className="brand-mark"><HeartPulse size={22}/></span><span><b>FrailtyScope</b><small>AGEING & HEALTH INTELLIGENCE</small></span></Link><nav className="portal-nav" aria-label="Portal navigation"><Link href="/doctor" aria-current={!research?'page':undefined} className={!research?'nav-active':''}><Stethoscope size={17}/> Doctor</Link><Link href="/admin" aria-current={research?'page':undefined} className={research?'nav-active':''}><BarChart3 size={17}/> Research</Link></nav><div className="header-status">PUBLIC SURVEY EVIDENCE · DEMO</div></div></header>
}
