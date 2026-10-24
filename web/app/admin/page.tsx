import type {Metadata} from 'next';
import {redirect} from 'next/navigation';
import {canViewPublicDashboard} from '../lib/auth';
import {signOut} from './actions';
import {ResearchDashboard} from '../ui/research-dashboard';

export const metadata: Metadata = {title: 'Research · FrailtyScope'};
export const dynamic = 'force-dynamic';

export default async function AdminPage() {
  if (!(await canViewPublicDashboard())) redirect('/admin/login');
  return (
    <main id="main">
      <ResearchDashboard
        actions={<form action={signOut}><button className="fs-signout" type="submit">Sign out</button></form>}
      />
    </main>
  );
}
