'use client';

import { useEffect, useState } from 'react';
import { GitCommitHorizontal, ShieldCheck } from 'lucide-react';

type ReleaseStatus = {
  schema: string;
  release: string;
  deployment: {git_commit:string|null;git_identity_available:boolean};
  evidence: {new_real_data_execution:string;clinical_prediction:boolean};
};

export function ReleaseStatusV34() {
  const [receipt,setReceipt] = useState<ReleaseStatus|null>(null);
  const [error,setError] = useState(false);
  useEffect(()=>{
    const abort=new AbortController();
    fetch('/api/status',{cache:'no-store',signal:abort.signal})
      .then(r=>{if(!r.ok)throw new Error('HTTP status unavailable'); return r.json();})
      .then((data:ReleaseStatus)=>{
        if(data.schema!=='FRAILTYSCOPE_PUBLIC_RELEASE_STATUS_V34' || data.release!=='v0.34' ||
          data.evidence?.new_real_data_execution!=='BLOCKED_FOR_NEW_ANALYSIS' || data.evidence?.clinical_prediction!==false) {
          throw new Error('Invalid status contract');
        }
        setReceipt(data);
      })
      .catch(()=>{if(!abort.signal.aborted)setError(true);});
    return ()=>abort.abort();
  },[]);
  return <div className="v34-release" aria-label="Published software release identity" role="status">
    <div><GitCommitHorizontal size={19}/><span><b>Software release</b><small>{receipt?.release || (error?'Unverified':'Checking deployment…')}</small></span></div>
    <div><ShieldCheck size={19}/><span><b>Git deployment identity</b><small>{receipt?.deployment.git_commit ? receipt.deployment.git_commit.slice(0,12) : 'Not available from this deployment'}</small></span></div>
    <p>Identity comes from the deployment environment when available. Historical NHANES results remain unchanged; no live model fitting or clinical predictions.</p>
  </div>;
}
