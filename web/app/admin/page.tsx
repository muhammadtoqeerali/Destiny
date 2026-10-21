import { redirect } from 'next/navigation';
import { AdminResearchHub } from '../components/multi-outcome-admin';
import { hasAdminSession } from '../lib/auth';
import { signOut } from './actions';
import { LogOut, ShieldCheck } from 'lucide-react';
export const dynamic = 'force-dynamic';
export default async function AdminPage(){
  if (!(await hasAdminSession())) redirect('/admin/login');
  return <div className="page-wrap admin-page">
    <div className="portal-strip"><div><span className="portal-label"><ShieldCheck size={16}/> Research administration</span><p>Dataset assessment and model analytics</p></div><form action={signOut}><button className="text-button" type="submit"><LogOut size={16}/> Sign out</button></form></div>
    <AdminResearchHub/>
  </div>;
}
