'use client';

import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {Activity, BarChart3, FlaskConical, LockKeyhole, Menu, X} from 'lucide-react';
import {useState} from 'react';

/** Brand and navigation only; NTNU lettering is an unlicensed placeholder, not an official institutional logo. */
export default function SiteHeader(){
  const path=usePathname();
  const [open,setOpen]=useState(false);
  const doctor=path.startsWith('/doctor')||path==='/'||path==='/interview';
  const close=()=>setOpen(false);
  return <header className="fs66-header">
    <div className="fs66-nav-shell">
      <Link href="/doctor" className="fs66-brand" onClick={close} aria-label="FrailtyScope home">
        <span className="fs66-brand-icon"><Activity size={21} strokeWidth={2.5}/></span>
        <span className="fs66-brand-copy"><strong>Frailty<span>Scope</span></strong><small>AGEING RESEARCH STUDIO</small></span>
      </Link>
      <span className="fs66-academic-lockup" title="NTNU text placeholder — not an official university logo">NTNU <small>concept</small></span>
      <button className="fs66-menu-button" type="button" onClick={()=>setOpen(o=>!o)} aria-expanded={open} aria-controls="fs66-site-nav" aria-label={open?'Close navigation':'Open navigation'}>{open?<X size={22}/>:<Menu size={22}/>}</button>
      <nav id="fs66-site-nav" className={'fs66-nav'+(open?' is-open':'')} aria-label="Main navigation">
        <Link href="/doctor" onClick={close} aria-current={doctor?'page':undefined} className={doctor?'fs66-nav-active':''}><Activity size={16}/> Overview</Link>
        <Link href="/doctor#cases" onClick={close}><FlaskConical size={16}/> Case studio</Link>
        <Link href="/doctor#evidence" onClick={close}><BarChart3 size={16}/> Evidence</Link>
        <Link href="/admin" onClick={close} aria-current={path.startsWith('/admin')?'page':undefined} className={path.startsWith('/admin')?'fs66-nav-active':''}><LockKeyhole size={16}/> Research / Admin</Link>
      </nav>
    </div>
  </header>;
}
