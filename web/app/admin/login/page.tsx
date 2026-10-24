import type {Metadata} from 'next';
import Link from 'next/link';
import {redirect} from 'next/navigation';
import {canViewPublicDashboard} from '../../lib/auth';
import {signIn} from '../actions';
import {BrandMark} from '../../ui/brand';

export const metadata: Metadata = {title: 'Sign in · FrailtyScope'};
export const dynamic = 'force-dynamic';

export default async function LoginPage({searchParams}: {searchParams: Promise<{error?: string}>}) {
  if (await canViewPublicDashboard()) redirect('/admin');
  const invalid = (await searchParams).error === 'invalid';
  return (
    <main id="main" className="fs-wrap fs-login">
      <div className="fs-surface fs-login-card">
        <BrandMark size={40} />
        <div style={{display: 'grid', gap: '.4rem'}}>
          <h1 className="fs-h2">Research dashboard</h1>
          <p className="fs-muted">Sign in to see the experiment behind the Doctor view: data, models, evaluation and limits. It shows published aggregate results only.</p>
        </div>
        <form action={signIn} style={{display: 'grid', gap: '1rem'}}>
          <div className="fs-field">
            <label htmlFor="admin-password">Access password</label>
            <input id="admin-password" name="password" type="password" autoComplete="current-password" required minLength={1}
              aria-invalid={invalid || undefined} aria-describedby={invalid ? 'login-error' : undefined} />
            {invalid && <p className="fs-error" id="login-error" role="alert">Incorrect password.</p>}
          </div>
          <button className="fs-btn" type="submit">Open research workspace</button>
        </form>
        <Link className="fs-link" href="/doctor">Back to the Doctor view</Link>
      </div>
    </main>
  );
}
