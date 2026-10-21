"""Add evidence-based benchmark tab to CURRENT Admin portal without replacing its content."""
from __future__ import annotations
import argparse
from pathlib import Path

TYPE_BEFORE = "type Section = 'Dataset' | 'Preprocessing' | 'Model training' | 'Performance' | 'Interpretability';"
TYPE_AFTER = "type Section = 'Dataset' | 'Preprocessing' | 'Model training' | 'Performance' | 'Interpretability' | 'Benchmark';"
STEPS_BEFORE = "const steps:Section[]=['Dataset','Preprocessing','Model training','Performance','Interpretability'];"
STEPS_AFTER = "const steps:Section[]=['Dataset','Preprocessing','Model training','Performance','Interpretability','Benchmark'];"
ANCHOR = "   {tab==='Interpretability'&&<>"
BLOCK = '''   {tab==='Benchmark'&&<>
    <Lead code="COMPARATIVE VALIDATION" title="Reference and optimized models" subtitle="Two model-selection procedures evaluated on the same later NHANES cycle. Thresholds were selected using development data."/>
    <div className="v7-stats"><div><span>Evaluation participants</span><strong>{study.counts.test.toLocaleString()}</strong><small>2013–2014 survey cycle</small></div><div><span>Reference model</span><strong className="v7-wordstat">{study.selectedModel}</strong><small>Validation-selected baseline</small></div><div><span>Optimized model</span><strong className="v7-wordstat">{refined.selectedModel}</strong><small>Cross-validated parameter search</small></div><div><span>Observed events</span><strong>{study.counts.test_events}</strong><small>Approximately 60-month outcome</small></div></div>
    <Panel title="Later-cycle model comparison" subtitle="Distinct models and decision thresholds; evaluated on the same later-cycle research records">
      <div className="v7-table-wrap"><table className="v7-table"><thead><tr><th>Experiment</th><th>Model</th><th>ROC-AUC</th><th>Brier ↓</th><th>Recall</th><th>Precision</th><th>F1</th><th>Cutoff</th></tr></thead><tbody>
       <tr><td>Reference</td><td>{study.selectedModel}</td><td>{study.testAtF2.roc_auc.toFixed(3)}</td><td>{study.testAtF2.brier.toFixed(3)}</td><td>{pct(study.testAtF2.recall)}</td><td>{pct(study.testAtF2.precision)}</td><td>{study.testAtF2.f1.toFixed(3)}</td><td>{study.threshold.toFixed(3)}</td></tr>
       <tr><td>Optimized</td><td>{refined.selectedModel}</td><td>{refined.test.roc_auc.toFixed(3)}</td><td>{refined.test.brier.toFixed(3)}</td><td>{pct(refined.test.recall)}</td><td>{pct(refined.test.precision)}</td><td>{refined.test.f1.toFixed(3)}</td><td>{refined.selectedThreshold.toFixed(3)}</td></tr>
      </tbody></table></div>
    </Panel>
    <div className="v7-two">
      <Panel title="Event classifications" subtitle="Counts at each model's validation-selected threshold"><div className="v7-table-wrap"><table className="v7-table"><thead><tr><th>Outcome</th><th>Reference</th><th>Optimized</th></tr></thead><tbody>
       {([['Detected events',study.testAtF2.confusion.tp,refined.test.confusion.tp],['Missed events',study.testAtF2.confusion.fn,refined.test.confusion.fn],['False-positive classifications',study.testAtF2.confusion.fp,refined.test.confusion.fp],['Correct non-events',study.testAtF2.confusion.tn,refined.test.confusion.tn]] as [string,number,number][]).map(([label,a,b])=><tr key={label}><td>{label}</td><td>{a}</td><td>{b}</td></tr>)}
      </tbody></table></div></Panel>
      <Panel title="How models are selected"><div className="v7-domain-list"><div><span className="v7-dot"/><strong>Primary objective</strong><p>Model selection uses validation probability error (Brier score), not the evaluation cohort.</p></div><div><span className="v7-dot"/><strong>Operating threshold</strong><p>Each experiment selects its threshold on development data using F2. Higher recall can also create more false positives.</p></div><div><span className="v7-dot"/><strong>Evaluation boundary</strong><p>The later NHANES cycle has been examined in previous experiments; these findings are not independent external validation.</p></div></div></Panel>
    </div>
   </>}
'''


def patch(src:str)->str:
    if "tab==='Benchmark'" in src:
        if TYPE_AFTER in src and STEPS_AFTER in src:return src
        raise ValueError('Partial benchmark integration; inspect manually')
    for fragment in (TYPE_BEFORE,STEPS_BEFORE,ANCHOR):
        if src.count(fragment)!=1:raise ValueError('Cannot uniquely locate current Admin portal anchor: '+fragment)
    return src.replace(TYPE_BEFORE,TYPE_AFTER).replace(STEPS_BEFORE,STEPS_AFTER).replace(ANCHOR,BLOCK+ANCHOR)


def main():
    p=argparse.ArgumentParser();p.add_argument('file');args=p.parse_args()
    target=Path(args.file);source=target.read_text()
    updated=patch(source)
    if updated!=source:target.write_text(updated)
    print('PASS: Real-data reference-versus-optimized Benchmark tab')
if __name__=='__main__':main()
