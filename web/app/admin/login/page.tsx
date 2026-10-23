import { redirect } from 'next/navigation';
import { LockKeyhole, ShieldCheck, ArrowRight, Info } from 'lucide-react';
import { canViewPublicDashboard } from '../../lib/auth';
import { signIn } from '../actions';
export const dynamic = 'force-dynamic';
export default async function LoginPage({searchParams}:{searchParams:Promise<{error?:string}>}){
  if(await canViewPublicDashboard()) redirect('/admin');
  const invalid=(await searchParams).error==='invalid';
  return <main className="login-stage"><div className="login-decoration"><div className="pattern-disc"/><div className="login-mark"><ShieldCheck size={24}/></div><p>FRAILTY INTELLIGENCE / RESEARCH OPERATIONS</p><h1>Research operations and model analytics.</h1><span>Data provenance, preprocessing, performance and interpretability in one workspace.</span><div className="login-foot">FrailtyScope · Administrative workspace</div></div>
    <div className="login-side"><div className="login-panel"><div className="login-icon"><LockKeyhole size={24}/></div><span className="micro-label">ADMIN PORTAL</span><h2>Sign in</h2><p className="login-subtitle">Explore reproducible ML workflows and historical research analytics.</p>
      <form action={signIn} className="login-form"><label htmlFor="admin-password">Access password</label><input id="admin-password" name="password" type="password" autoComplete="current-password" placeholder="Enter password" required minLength={1}/>{invalid&&<p className="form-error" role="alert">Incorrect password.</p>}<button className="primary-action" type="submit">Open research workspace <ArrowRight size={18}/></button></form>
      <div className="auth-notice"><Info size={17}/><span>Administrative access is intended for aggregate research reports. Do not upload identifiable medical records.</span></div>
      <a href="/doctor" className="login-back">Doctor Portal →</a>
    </div></div>
  </main>;
}
