import {redirect} from 'next/navigation';
// Old bookmark: forwards to the canonical Research view, which performs its own sign-in check.
export const dynamic = 'force-dynamic';
export default function LegacyResearchPath() { redirect('/admin'); }
