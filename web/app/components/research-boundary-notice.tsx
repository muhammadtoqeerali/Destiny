/** Research-readiness notice shared by the historical Doctor and Admin dashboards.
 * This is documentary, not a claim that a study or model has been re-evaluated.
 */
export function ResearchBoundaryNotice() {
  return <aside role="note" className="v31-research-boundary">
    <strong>Historical NHANES 5-year mortality research — not a clinical prediction service</strong>
    <p>These published aggregates come from different earlier modeling experiments. The 2013–2014 survey cycle was previously inspected and is not untouched independent validation. FrailtyScope v0.30 added synthetic-only software integrity checks and a chart repair, not new NHANES results. The original case remains BLOCKED_FOR_NEW_ANALYSIS with a provisional prediction index and 11 unmapped predictors. No individual risk is computed here.</p>
  </aside>;
}
