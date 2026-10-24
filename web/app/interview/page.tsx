import {redirect} from 'next/navigation';
// Old bookmark: forwards to the canonical Doctor view. Not linked from anywhere.
export default function LegacyDoctorPath() { redirect('/doctor'); }
