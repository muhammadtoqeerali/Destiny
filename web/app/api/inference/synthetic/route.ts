import {NextRequest,NextResponse} from 'next/server';
import {calculateSyntheticFixture,fixtureAllowed,servingSafetyGate} from '../../../lib/synthetic-serving-v40';

export const dynamic='force-dynamic';
export const revalidate=0;
const headers={'Cache-Control':'no-store, max-age=0, must-revalidate','X-Content-Type-Options':'nosniff'};
const respond=(data:unknown,status:number)=>NextResponse.json(data,{status,headers});

/** Only enumerated artificial fixtures. No free-form fields, clinical model, cookies or body parsing. */
export async function GET(request:NextRequest){
  if(!servingSafetyGate())return respond({error:'SYNTHETIC_REGISTRY_GATE_CLOSED'},503);
  const params=request.nextUrl.searchParams;
  if([...params.keys()].some(k=>k!=='fixture') || params.getAll('fixture').length!==1 ||
      !fixtureAllowed(params.get('fixture')||'')) {
    return respond({error:'ONLY_PREDEFINED_FICTIONAL_FIXTURES'},400);
  }
  const fixture=params.get('fixture')!;
  if(!fixtureAllowed(fixture))return respond({error:'ONLY_PREDEFINED_FICTIONAL_FIXTURES'},400);
  return respond(calculateSyntheticFixture(fixture),200);
}
export async function POST(){return respond({error:'SYNTHETIC_ENDPOINT_READ_ONLY'},405);}
export async function PUT(){return respond({error:'SYNTHETIC_ENDPOINT_READ_ONLY'},405);}
export async function PATCH(){return respond({error:'SYNTHETIC_ENDPOINT_READ_ONLY'},405);}
export async function DELETE(){return respond({error:'SYNTHETIC_ENDPOINT_READ_ONLY'},405);}
