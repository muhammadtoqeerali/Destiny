import { NextResponse } from 'next/server';

/** Public source/version receipt. No credentials, headers or private research files. */
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET() {
  // This env var is set by Vercel's Git integration when available. Null is honest.
  const candidate = process.env.VERCEL_GIT_COMMIT_SHA || '';
  const gitCommit = /^[a-f0-9]{40}$/i.test(candidate) ? candidate.toLowerCase() : null;
  const response = NextResponse.json({
    schema: 'FRAILTYSCOPE_PUBLIC_RELEASE_STATUS_V34',
    release: 'v0.34',
    application: 'FrailtyScope',
    deployment: { git_commit: gitCommit, git_identity_available: gitCommit !== null },
    evidence: {
      historical_nhanes: 'previously_published_aggregates_only',
      synthetic_workflow: 'verified_documentary_receipt_v30',
      new_real_data_execution: 'BLOCKED_FOR_NEW_ANALYSIS',
      clinical_prediction: false,
    },
  });
  response.headers.set('Cache-Control', 'no-store, max-age=0, must-revalidate');
  response.headers.set('X-Content-Type-Options', 'nosniff');
  return response;
}
