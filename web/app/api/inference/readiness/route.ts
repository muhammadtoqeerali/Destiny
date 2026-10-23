import {NextResponse} from 'next/server';
import receipt from '../../../data/inference-readiness-v39.json';

/** Public research-readiness receipt only; no patient data or clinical scoring. */
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET() {
  // A case configuration change cannot enable clinical inference through this endpoint.
  if (receipt.clinical_inference !== false || receipt.registered_clinical_models !== 0 ||
      receipt.governance_status !== 'BLOCKED_FOR_NEW_ANALYSIS') {
    return NextResponse.json({error:'INTEGRITY_GATE_CLOSED'}, {status:503,
      headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
  }
  return NextResponse.json(receipt, {status:200,
    headers:{'Cache-Control':'no-store, max-age=0, must-revalidate',
      'X-Content-Type-Options':'nosniff'}});
}
// Disallow submitting patient details or attempts to turn readiness into prediction.
export async function POST() {
  return NextResponse.json({error:'READINESS_ENDPOINT_IS_READ_ONLY'}, {status:405,
    headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',Allow:'GET'}});
}
