import {NextResponse} from 'next/server';

/** Never accepts patient inputs. A future separate authenticated app/service must earn approval. */
export const dynamic='force-dynamic';
export const revalidate=0;
const blocked={
  schema:'FRAILTYSCOPE_INFERENCE_GATE_V38',
  status:'BLOCKED_FOR_NEW_ANALYSIS',
  clinical_inference:false,
  registered_clinical_models:0,
  supported_person_level_outcomes:[],
  reason:'No authorized patient-level model, validation, mapping or clinical-use approval exists.'
};
function response(){
  const result=NextResponse.json(blocked,{status:403});
  result.headers.set('Cache-Control','no-store, max-age=0, must-revalidate');
  result.headers.set('X-Content-Type-Options','nosniff');
  return result;
}
// Intentionally never parses, logs, processes or persists any request body.
export async function POST(){return response();}
export async function PUT(){return response();}
export async function GET(){return response();}
