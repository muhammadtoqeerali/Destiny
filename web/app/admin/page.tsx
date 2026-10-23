import { redirect } from 'next/navigation';
import { AdminResearchHub } from '../components/multi-outcome-admin';
import { canViewPublicDashboard, hasPublicDemoSession } from '../lib/auth';
import { signOut } from './actions';
import { LogOut, ShieldCheck } from 'lucide-react';
export const dynamic = 'force-dynamic';
export default async function AdminPage(){
  if (!(await canViewPublicDashboard())) redirect('/admin/login');
  const publicDemo = await hasPublicDemoSession();
  return <div className="page-wrap admin-page">
    {publicDemo && <aside className="v32-demo-banner" role="note"><strong>Public demonstration workspace — not secure research administration</strong>Only historically published NHANES aggregates and documentary synthetic software status are visible. Passcode admin123 is a demo convenience, not authorization to access private participant data or run models.</aside>}
    <div className="portal-strip"><div><span className="portal-label"><ShieldCheck size={16}/> Research administration</span><p>Dataset assessment and model analytics</p></div><form action={signOut}><button className="text-button" type="submit"><LogOut size={16}/> Sign out</button></form></div>
    <AdminResearchHub/>
  </div>;
}
