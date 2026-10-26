'use client';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {HeartPulse, LockKeyhole, Stethoscope} from 'lucide-react';
export default function SiteHeader(){
 const path=usePathname();const inAdmin=path.startsWith('/admin');
 return <header className="site-header"><div className="site-header-inner"><Link href="/doctor" className="site-brand" aria-label="FrailtyScope home"><span className="brand-mark"><HeartPulse size={22}/></span><span><b>FrailtyScope</b><small>AGEING & HEALTH INTELLIGENCE</small></span></Link><nav className="portal-nav" aria-label="Portal navigation"><Link href="/doctor" className={path.startsWith('/doctor')||path==='/interview'?'nav-active':''}><Stethoscope size={17}/> Doctor</Link><Link href="/admin" className={inAdmin?'nav-active':''}><LockKeyhole size={17}/> Research / Admin</Link></nav></div></header>;
}
