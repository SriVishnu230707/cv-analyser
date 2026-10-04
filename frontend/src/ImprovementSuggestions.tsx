import { useState } from 'react';
import type { ComparisonReport } from './types';

export function ImprovementSuggestions({ report }: { report: ComparisonReport }) {
  const [priority, setPriority] = useState('all');
  const [copied, setCopied] = useState('');
  const [copyError, setCopyError] = useState('');
  const items = report.suggestions.filter(item => priority === 'all' || item.priority === priority);
  async function copy(id: string, text: string) {
    try { await navigator.clipboard.writeText(text); setCopied(id); setCopyError(''); }
    catch { setCopyError('Copy is unavailable here. Select the rewrite text and copy it manually.'); }
  }
  return <section className="card suggestion-panel" aria-labelledby="suggestion-title">
    <div className="section-heading"><div><span className="eyebrow">05 · MAKE THE NEXT EDIT COUNT</span><h2 id="suggestion-title">Your improvement plan</h2></div><span className="pill">{report.suggestions.length} suggestions</span></div>
    <p className="muted">Start with the highest-priority findings. Suggestions help you document real experience; they do not add missing skills or guarantee a higher score.</p>
    {report.resume_quality ? <div className="quality-checks"><h3>Resume quality and editing checks</h3><p className="muted">Checks to review: {report.resume_quality.review_count}. {report.resume_quality.disclaimer}</p>{report.resume_quality.checks.map(check => <article className="quality-check" key={check.id}><div className="suggestion-heading"><span className={'priority ' + (check.status === 'pass' ? 'low' : 'high')}>{check.status === 'pass' ? 'Detected' : 'Review'}</span><h4>{check.title}</h4></div><p className="suggestion-rationale">{check.finding}</p>{check.action ? <p className="suggestion-action">{check.action}</p> : null}</article>)}</div> : null}
    <label htmlFor="suggestion-priority">Filter by priority</label><select id="suggestion-priority" value={priority} onChange={event => setPriority(event.target.value)}><option value="all">All priorities</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select>
    {items.length ? items.map(item => <article className="suggestion-item" key={item.id}><div className="suggestion-heading"><span className={'priority ' + item.priority}>{item.priority} priority</span><h3>{item.kind.replaceAll('_', ' ')}</h3></div>{item.requirement_ids.length ? <div className="suggestion-requirements">{item.requirement_ids.map(id => <span key={id}>{report.requirements.find(requirement => requirement.id === id)?.name}</span>)}</div> : null}<p className="suggestion-rationale">{item.rationale}</p><p className="suggestion-action">{item.action}</p>
      {item.evidence ? <details><summary>Current resume evidence · {item.evidence.section}</summary><blockquote>{item.evidence.text}</blockquote></details> : null}
      {item.rewrite ? <div className="rewrite-box"><h4>Suggested wording from your existing text</h4><blockquote>{item.rewrite}</blockquote><button type="button" className="text-button" onClick={() => void copy(item.id, item.rewrite!)}>{copied === item.id ? 'Copied' : 'Copy suggested wording'}</button><small>Review before using. This is not applied to your resume automatically.</small></div> : null}
    </article>) : <p className="empty-profile">{report.suggestions.length ? 'No suggestions at this priority.' : 'No actionable findings were identified by the current rules. You can still review every evidence match above.'}</p>}
    <p className="copy-status" role="status" aria-live="polite">{copyError || (copied ? 'Suggested wording copied.' : '')}</p>
    <p className="muted">Edit the resume preview above, review it again, and compare to refresh this plan.</p>
  </section>;
}
