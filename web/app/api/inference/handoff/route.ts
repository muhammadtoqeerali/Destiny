import {NextRequest,NextResponse} from 'next/server';
import receipt from '../../../data/study-handoff-v44.json';
export const dynamic='force-dynamic';
export const revalidate=0;
const headers={'Cache-Control':'no-store, max-age=0, must-revalidate','X-Content-Type-Options':'nosniff'};
const respond=(data:unknown,status:number)=>NextResponse.json(data,{status,headers});
/** Source-only study-team checklist; no clinical model, request body, or patient data. */
export async function GET(request:NextRequest){
  if(request.nextUrl.search!=='')return respond({error:'PUBLIC_HANDOFF_NO_QUERY_PARAMETERS'},400);
  if(receipt.schema!=='FRAILTYSCOPE_STUDY_HANDOFF_V44' ||
     receipt.scope!=='PUBLIC_RESEARCH_HANDOFF_NO_APPROVALS_OR_PATIENT_DATA' ||
     receipt.clinical_inference!==false || receipt.registered_clinical_models!==0 ||
     receipt.clinical_promotion_decision!=='DENIED' || receipt.approval_documents_received!==0 ||
     receipt.mapping_summary.prediction_time_approvals!==0 ||
     receipt.feature_evidence_requests.length!==14 ||
     receipt.feature_evidence_requests.some(f=>f.prediction_time_status!=='NOT_APPROVED'||f.signed_review_received!==false) ||
     receipt.outcome_evidence_requests.length!==4 ||
     receipt.outcome_evidence_requests.some(o=>o.individual_scoring_available!==false||o.evidence_received!==false) ||
     receipt.governance_requests.length!==7 || receipt.governance_requests.some(g=>g.approval_verified!==false)){
    return respond({error:'STUDY_HANDOFF_INTEGRITY_GATE_CLOSED'},503);
  }
  return respond(receipt,200);
}
export async function POST(){return respond({error:'STUDY_HANDOFF_IS_READ_ONLY'},405);}
export async function PUT(){return respond({error:'STUDY_HANDOFF_IS_READ_ONLY'},405);}
export async function PATCH(){return respond({error:'STUDY_HANDOFF_IS_READ_ONLY'},405);}
export async function DELETE(){return respond({error:'STUDY_HANDOFF_IS_READ_ONLY'},405);}
