import {NextRequest,NextResponse} from 'next/server';
import receipt from '../../../data/validation-readiness-v41.json';

/** Immutable public documentary and invented-only evaluation. No patient inference. */
export const dynamic='force-dynamic';
export const revalidate=0;
const headers={'Cache-Control':'no-store, max-age=0, must-revalidate','X-Content-Type-Options':'nosniff'};
const respond=(data:unknown,status:number)=>NextResponse.json(data,{status,headers});
const safe=()=>receipt.schema==='FRAILTYSCOPE_VALIDATION_REHEARSAL_V41' &&
  receipt.mode==='PUBLIC_DOCUMENTS_AND_INVENTED_RECORDS_ONLY' &&
  receipt.clinical_inference===false && receipt.registered_clinical_models===0 &&
  receipt.scientific_readiness.clinical_inference===false &&
  receipt.scientific_readiness.registered_clinical_models===0 &&
  receipt.fictional_validation.patient_data_used===false &&
  receipt.fictional_validation.independent_clinical_validation===false;
export async function GET(request:NextRequest){
  if(!safe())return respond({error:'VALIDATION_GATE_CLOSED'},503);
  if([...request.nextUrl.searchParams.keys()].length!==0)
    return respond({error:'VALIDATION_ENDPOINT_NO_INPUT'},400);
  return respond(receipt,200);
}
export async function POST(){return respond({error:'VALIDATION_ENDPOINT_READ_ONLY'},405);}
export async function PUT(){return respond({error:'VALIDATION_ENDPOINT_READ_ONLY'},405);}
export async function PATCH(){return respond({error:'VALIDATION_ENDPOINT_READ_ONLY'},405);}
export async function DELETE(){return respond({error:'VALIDATION_ENDPOINT_READ_ONLY'},405);}
