import {redirect} from 'next/navigation';
import {canViewPublicDashboard} from '../lib/auth';
import {signOut} from './actions';
import {LogOut} from 'lucide-react';
import {ResearchFocusV50} from '../components/research-focus-v50';
export const dynamic='force-dynamic';
export default async function AdminPage(){
 if(!(await canViewPublicDashboard())) redirect('/admin/login');
 return <><ResearchFocusV50/><div className="focus-session-footer"><form action={signOut}><button type="submit"><LogOut size={15}/> Sign out</button></form></div></>;
}
