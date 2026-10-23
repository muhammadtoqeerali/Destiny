import {NextResponse} from 'next/server';
import report from '../../../data/model-translation-v42.json';

export const dynamic='force-dynamic';
export const revalidate=0;
const headers={'Cache-Control':'no-store, max-age=0, must-revalidate','X-Content-Type-Options':'nosniff'};

/** Public documentary crosswalk only. Never reads any patient submission/body. */
export async function GET(){
  if(report.schema!=='FRAILTYSCOPE_SOURCE_TO_FORM_PROMOTION_V42' ||
     report.clinical_inference!==false || report.registered_clinical_models!==0 ||
     report.clinical_promotion_decision!=='DENIED' ||
     report.features.length!==14 || report.prediction_time_approvals!==0 ||
     report.outcome_promotion.some(x=>x.clinical_prediction_available!==false)){
    return NextResponse.json({error:'PROMOTION_GATE_CLOSED'},{status:503,headers});
  }
  return NextResponse.json(report,{status:200,headers});
}
export async function POST(){return NextResponse.json({error:'DOCUMENTARY_ENDPOINT_READ_ONLY'},{status:405,headers:{...headers,Allow:'GET'}});}
export async function PUT(){return NextResponse.json({error:'DOCUMENTARY_ENDPOINT_READ_ONLY'},{status:405,headers:{...headers,Allow:'GET'}});}
