#!/usr/bin/env python3
"""Source-only, strict-marker patch for FrailtyScope website research reporting.

Designed for published v0.30 only. No participant, model, private audit or public
aggregate data are read, written or analyzed. Installer verifies Git HEAD first.
"""
from pathlib import Path
import sys


def apply(path: Path, edits: list[tuple[str, str]]) -> None:
    source = path.read_text(encoding="utf-8")
    result = source
    for before, after in edits:
        n = result.count(before)
        if n != 1:
            raise ValueError(f"Refusing to edit {path}: expected one matching source marker, found {n}: {before[:100]!r}")
        result = result.replace(before, after, 1)
    if result == source:
        raise ValueError(f"Expected actual change: {path}")
    path.write_text(result, encoding="utf-8")
    print(f"PATCHED: {path}")


def main(root: Path):
    apply(root / "web/app/components/decision-quality-v12.tsx", [
        ("useState(String(locked))", "useState(String(closest.threshold))"),
        ("Development-locked model and threshold; later-cycle observations are used for evaluation only. All results are NHANES aggregates.",
         "Historical development-selected model and threshold; 2013–2014 observations were previously inspected in earlier releases. These are published NHANES aggregates, not fresh independent validation."),
        ("Uncertainty around the final evaluation", "Exploratory uncertainty around historical evaluation"),
        ("Independent experiment records: descriptive comparison", "Distinct historical experiments: descriptive comparison"),
    ])
    apply(root / "web/app/components/evidence-workbench-v11.tsx", [
        ("Reproducible cohort analysis, fitted transformation evidence, model comparison, and independent evaluation.",
         "Historical cohort analysis, fitted transformation evidence, model comparison, and previously inspected later-cycle evaluation; not fresh independent validation."),
    ])
    apply(root / "web/app/components/multi-outcome-admin.tsx", [
        ("import { DecisionQualityV12 } from './decision-quality-v12';",
         "import { DecisionQualityV12 } from './decision-quality-v12';\nimport { ResearchBoundaryNotice } from './research-boundary-notice';"),
        ("{tab==='Dataset'&&<>", "<ResearchBoundaryNotice/>\n    {tab==='Dataset'&&<>"),
        ("title=\"Discrimination and operating characteristics\" subtitle=\"Results on 2013–2014 NHANES after model selection using the earlier cycle.\"",
         "title=\"Discrimination and operating characteristics\" subtitle=\"Historical results on the previously inspected 2013–2014 NHANES cycle after development selection in 2011–2012; not a fresh independent evaluation.\""),
        ("title=\"Reference and optimized models\" subtitle=\"Two model-selection procedures evaluated on the same later NHANES cycle. Thresholds were selected using development data.\"",
         "title=\"Reference and optimized historical experiments\" subtitle=\"Two different model-selection protocols evaluated on the same previously inspected 2013–2014 NHANES cycle. Neither is a new independent test.\""),
    ])
    apply(root / "web/app/components/clinical-workspace.tsx", [
        ("import profiles from '../../public/data/nhanes-cohort-profile.json';",
         "import profiles from '../../public/data/nhanes-cohort-profile.json';\nimport { ResearchBoundaryNotice } from './research-boundary-notice';"),
        ("const clinicalPct=(x:number)=>(x*100).toFixed(1)+'%';",
         """const clinicalPct=(x:number)=>(x*100).toFixed(1)+'%';
const isValidAssessment=(key:string, raw:string)=>{
  if(raw==='')return false;
  if(key==='age'){const n=Number(raw);return Number.isInteger(n)&&n>=65&&n<=110;}
  if(key==='bmi'){const n=Number(raw);return Number.isFinite(n)&&n>=10&&n<=70;}
  if(key==='phq9_score'){const n=Number(raw);return Number.isInteger(n)&&n>=0&&n<=27;}
  return true;
};"""),
        ("const recorded=Object.values(profile).filter(v=>v!==''&&v!==undefined).length;",
         "const recorded=Object.entries(profile).filter(([key,value])=>isValidAssessment(key,value)).length;\n const invalidEntries=Object.entries(profile).filter(([key,value])=>value!==''&&!isValidAssessment(key,value));"),
        ("const mobility=MOBILITY.filter(k=>profile[k]&&profile[k]!=='No difficulty').map(k=>LABELS[k]);",
         "const mobility=MOBILITY.filter(k=>['Some difficulty','Much difficulty','Unable to do'].includes(profile[k])).map(k=>LABELS[k]);"),
        ("{page==='Population overview'&&<>", "<ResearchBoundaryNotice/>\n  {page==='Population overview'&&<>"),
        ("<span>Held-out ROC-AUC</span>", "<span>Historical later-cycle ROC-AUC</span>"),
        ("<option>Unable to do</option></select></label>)}</div></Box>",
         "<option>Unable to do</option><option>Does not do activity</option><option>Not asked (structural skip)</option><option>Refused</option><option>Don't know</option></select></label>)}</div><p className=\"v7-fine\">Activity nonparticipation, structural skip and refusal are distinct missingness/status categories, not ordered difficulty severities.</p></Box>"),
        ("<span>fields recorded</span></div><div className=\"v7-completion-track\">",
         "<span>valid fields recorded</span></div>{invalidEntries.length>0&&<p role=\"alert\" className=\"v7-fine\">{invalidEntries.length} numeric field(s) are outside the permitted range or not integers. Correct them before counting this assessment as complete.</p>}<div className=\"v7-completion-track\">"),
        ("Object.entries(LABELS).filter(([k])=>profile[k]).map",
         "Object.entries(LABELS).filter(([k])=>isValidAssessment(k,profile[k]||'')).map"),
    ])
    apply(root / "web/app/components/site-header.tsx", [
        ("REAL PUBLIC-USE RESEARCH", "HISTORICAL NHANES AGGREGATES"),
    ])
    apply(root / "web/app/globals.css", [
        ("*{box-sizing:border-box}",
         """.v31-research-boundary{padding:14px 18px;margin:8px 0 18px;background:#f5f9f8;border:1px solid #c9ded7;border-radius:12px;color:#365d62;font-size:13px;line-height:1.6}.v31-research-boundary strong{display:block;margin-bottom:4px;font-weight:800}.v31-research-boundary p{margin:0}*{box-sizing:border-box}"""),
    ])
    apply(root / "web/app/lib/auth.ts", [
        ("const password = () => process.env.ADMIN_PORTAL_PASSWORD || 'admin123';",
         "const password = () => process.env.ADMIN_PORTAL_PASSWORD || '';"),
        ("const secret = () => process.env.ADMIN_SESSION_SECRET || 'DEMO_ONLY_NOT_SECURE_' + password();",
         "const secret = () => process.env.ADMIN_SESSION_SECRET || '';\nconst configured = () => password().length >= 16 && secret().length >= 32 && password() !== secret();"),
        ("function signature(expiry: string): string {\n  return createHmac('sha256', secret()).update(expiry).digest('hex');\n}",
         "function signature(expiry: string): string {\n  if (!configured()) return '';\n  return createHmac('sha256', secret()).update(expiry).digest('hex');\n}"),
        ("export function matchesPassword(input: string): boolean {\n  const expected",
         "export function matchesPassword(input: string): boolean {\n  if (!configured()) return false;\n  const expected"),
        ("export async function openAdminSession() {\n  const expiry",
         "export async function openAdminSession() {\n  if (!configured()) throw new Error('Admin authentication has not been securely configured');\n  const expiry"),
        ("export async function hasAdminSession(): Promise<boolean> {\n  const token",
         "export async function hasAdminSession(): Promise<boolean> {\n  if (!configured()) return false;\n  const token"),
    ])
    apply(root / ".github/workflows/ci.yml", [
        ("tests/test_case_integrity_v30.py", "tests/test_case_integrity_v30.py tests/test_web_reporting_v31.py"),
    ])
    print("SOURCE-ONLY PATCH COMPLETE. No public aggregate, private artifact, or model files modified.")


if __name__ == '__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python scripts/patch_website_v31.py /absolute/project/root')
    main(Path(sys.argv[1]).resolve())
