import {redirect} from 'next/navigation';
import {canViewPublicDashboard} from '../../lib/auth';
import {InterviewAdminV47} from '../../components/interview-focus-v47';
export const dynamic='force-dynamic';
export default async function InterviewAdminPage(){
  if(!(await canViewPublicDashboard())) redirect('/admin/login');
  return <InterviewAdminV47/>;
}
