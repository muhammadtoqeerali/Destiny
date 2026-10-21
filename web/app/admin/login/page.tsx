import { redirect } from 'next/navigation';
import { LockKeyhole, ShieldCheck, ArrowRight, Info } from 'lucide-react';
import { hasAdminSession } from '../../lib/auth';
import { signIn } from '../actions';
export const dynamic = 'force-dynamic';
export default async function LoginPage({searchParams}:{searchParams:Promise<{error?:string}>}){
  if(await hasAdminSession()) redirect('/admin');
  const invalid=(await searchParams).error==='invalid';
  return <main className="login-stage"><div className="login-decoration"><div className="pattern-disc"/><div className="login-mark"><ShieldCheck size={24}/></div><p>FRAILTY INTELLIGENCE / RESEARCH ENVIRONMENT</p><h1>Understand each decision behind the model.</h1><span>Transparent experiments, reproducible preprocessing and measurable performance.</span><div className="login-foot">Clinical machine-learning research prototype</div></div>
    <div className="login-side"><div className="login-panel"><div className="login-icon"><LockKeyhole size={24}/></div><span className="micro-label">ADMIN PORTAL</span><h2>Welcome back</h2><p className="login-subtitle">Enter the demonstration password to view research tools and model development details.</p>
      <form action={signIn} className="login-form"><label htmlFor="admin-password">Admin password</label><input id="admin-password" name="password" type="password" autoComplete="current-password" placeholder="Enter password" required minLength={1}/>{invalid&&<p className="form-error" role="alert">Incorrect password. Try again.</p>}<button className="primary-action" type="submit">Access developer workspace <ArrowRight size={18}/></button></form>
      <div className="auth-notice"><Info size={17}/><span>This is a password gate for a public <strong>synthetic-data demo</strong>, not a security boundary for sensitive medical information. Never add real patient records.</span></div>
      <a href="/doctor" className="login-back">Continue to Doctor Portal instead →</a>
    </div></div>
  </main>;
}
