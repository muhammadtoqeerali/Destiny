/** Public fictional-model server math. Never accepts arbitrary observations or patient inputs. */
import registry from '../data/fictional-model-registry-v38.json';
import readiness from '../data/inference-readiness-v39.json';

export type FixtureId='fictional_reference'|'fictional_variant_b'|'fictional_variant_c';
const fixtures={
  fictional_reference:{age:75,bmi:26,phq:8,movement:0,history:0,smoking:0},
  fictional_variant_b:{age:82,bmi:30,phq:14,movement:1,history:1,smoking:1},
  fictional_variant_c:{age:68,bmi:22,phq:3,movement:2,history:0,smoking:0}
} as const;
export const fixtureOptions=[
  {id:'fictional_reference',label:'Fictional reference'},
  {id:'fictional_variant_b',label:'Fictional scenario B'},
  {id:'fictional_variant_c',label:'Fictional scenario C'}
] as const;
const featureKeys=['age_signal','bmi_signal','phq_signal','movement_signal','history_signal','smoking_signal'] as const;
const sigmoid=(x:number)=>1/(1+Math.exp(-x));
export function fixtureAllowed(id:string):id is FixtureId {
  return Object.prototype.hasOwnProperty.call(fixtures,id);
}
/** This is an independent hard gate, NOT controlled by HTTP parameters or environment toggles. */
export function servingSafetyGate(){
  return registry.provenance==='SYNTHETIC_GENERATED_ONLY' &&
    registry.independent_clinical_validation===false && registry.clinical_use_permitted===false &&
    registry.models.every(m=>m.clinical_use_permitted===false&&m.outcome_is_real===false&&m.trained_on==='generated_fictional_examples') &&
    readiness.clinical_inference===false && readiness.registered_clinical_models===0 &&
    readiness.governance_status==='BLOCKED_FOR_NEW_ANALYSIS';
}
/** No free-form feature object is accepted; only 3 enumerated invented fixtures. */
export function calculateSyntheticFixture(id:FixtureId){
  if(!servingSafetyGate())throw new Error('SYNTHETIC_REGISTRY_GATE_CLOSED');
  const f=fixtures[id];
  const signals={
    age_signal:(f.age-75)/10,bmi_signal:(f.bmi-26)/8,
    phq_signal:(f.phq-8)/8,movement_signal:f.movement/2,
    history_signal:f.history,smoking_signal:f.smoking
  };
  const results=registry.models.map(m=>{
    const contributions=featureKeys.map(feature=>({
      feature,signal:signals[feature],coefficient:m.weights[feature],
      log_odds_contribution:signals[feature]*m.weights[feature]
    }));
    const logit=m.intercept+contributions.reduce((sum,c)=>sum+c.log_odds_contribution,0);
    return {
      model_id:m.id,outcome_label:m.title,intercept:m.intercept,
      logit,synthetic_class_1_probability:sigmoid(logit),contributions
    };
  });
  return {
    schema:'FRAILTYSCOPE_SYNTHETIC_SERVING_V40',mode:'PREDEFINED_FICTIONAL_FIXTURE_ONLY',
    clinical_inference:false,patient_data_accepted:false,source_registry:registry.version,
    fixture_id:id,signals,results,
    disclaimer:'Only invented outcomes trained on generated examples. Not a patient prediction, medical risk, prognosis or real-disease model.'
  };
}
