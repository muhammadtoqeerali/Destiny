import {NextResponse} from 'next/server';
import receipt from '../../../data/artifact-acceptance-v43.json';
export const dynamic='force-dynamic';
export const revalidate=0;
const headers={'Cache-Control':'no-store, max-age=0, must-revalidate','X-Content-Type-Options':'nosniff'};
const result=(value:unknown,status:number)=>NextResponse.json(value,{status,headers});
/** Public synthetic metadata receipt. No artifact deserialization, query or patient input. */
export async function GET(){
  if(receipt.schema!=='FRAILTYSCOPE_ARTIFACT_ACCEPTANCE_V43' ||
     receipt.clinical_inference!==false || receipt.registered_clinical_models!==0 ||
     receipt.clinical_promotion_decision!=='DENIED' ||
     receipt.artifact_binary_loaded!==false || receipt.patient_data_used!==false ||
     receipt.clinical_outcomes.length!==4 ||
     receipt.clinical_outcomes.some(o=>o.decision!=='DENIED')){
    return result({error:'CLINICAL_ARTIFACT_GATE_CLOSED'},503);
  }
  return result(receipt,200);
}
export async function POST(){return result({error:'ARTIFACT_METADATA_READ_ONLY'},405);}
export async function PUT(){return result({error:'ARTIFACT_METADATA_READ_ONLY'},405);}
export async function PATCH(){return result({error:'ARTIFACT_METADATA_READ_ONLY'},405);}
export async function DELETE(){return result({error:'ARTIFACT_METADATA_READ_ONLY'},405);}
