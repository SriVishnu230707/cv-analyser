import { useEffect, useRef, useState } from 'react';
import { ArrowRight, LoaderCircle } from 'lucide-react';
import type { ComparisonReport, EvidenceDecision, PreparedResume } from './types';
import { categoryNames } from './StructuredProfile';
import { ImprovementSuggestions } from './ImprovementSuggestions';
import { checkedFetch, requestMessage } from './api';
import { fetchSkillCatalog } from './skillCatalog';
import { parseAIResponse, parseReport } from './reportValidation';
import { downloadResponse, saveReport } from './mobile';

interface Props { profile: PreparedResume; context: string | null }
const componentNames: Record<string, string> = { required_skills: 'Required skills', preferred_skills: 'Preferred skills', responsibilities: 'Responsibilities' };

export function ComparisonPanel({ profile, context }: Props) {
  const [report, setReport] = useState<ComparisonReport | null>(null);
  const [decisions, setDecisions] = useState<EvidenceDecision[]>([]);
  const [mappings, setMappings] = useState<Record<string, string>>({});
  const [catalog, setCatalog] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState('all');
  const [exporting, setExporting] = useState<'pdf' | 'json' | null>(null);
  const [exportError, setExportError] = useState('');
  const [downloadStatus, setDownloadStatus] = useState('');
  const [aiContext, setAiContext] = useState<string | null>(null);
  const [aiAvailable, setAiAvailable] = useState(false);
  const [aiConsent, setAiConsent] = useState(false);
  const [aiError, setAiError] = useState('');
  const [aiBusy, setAiBusy] = useState(false);
  const exportController = useRef<AbortController | null>(null);
  useEffect(() => () => exportController.current?.abort(), []);
  useEffect(() => {
    const controller = new AbortController();
    checkedFetch('/api/ai/status', { signal: controller.signal }).then(response => response.json()).then(body => { if (!controller.signal.aborted) setAiAvailable(body.configured === true); }).catch(() => { /* Local comparison remains usable. */ });
    fetchSkillCatalog(controller.signal).then(body => {
      if (!controller.signal.aborted) setCatalog(body.skills.map(item => item.name));
    }).catch(error => { if (!controller.signal.aborted) setError(requestMessage(error)); });
    return () => controller.abort();
  }, []);
  function requestBody(nextDecisions = decisions) {
    return { resume_text: profile.resume_text, job_description: profile.job_description, requirements_confirmed: true, category_corrections: profile.job_requirements.map(item => ({ requirement_id: item.id, category: item.category })), skill_mappings: Object.entries(mappings).filter(([, value]) => value).map(([id, value]) => ({ requirement_id: id, canonical_skill: value })), evidence_decisions: nextDecisions, extraction_context: context, ai_context: aiContext };
  }
  async function enhance() {
    if (busy || !report || !aiConsent || !aiAvailable || aiContext) return;
    setBusy(true); setAiBusy(true); setAiError(''); setError(''); setDownloadStatus('');
    const controller = new AbortController(); exportController.current = controller;
    try {
      const response = await checkedFetch('/api/ai/analyze', { method: 'POST', signal: controller.signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...requestBody(), cloud_consent: true }) });
      const body = parseAIResponse(await response.json(), report.input_hash);
      if (!controller.signal.aborted) { setAiContext(body.ai_context); setReport(body.report); }
    } catch (error) { if (!controller.signal.aborted) setAiError(requestMessage(error)); }
    finally { setBusy(false); setAiBusy(false); }
  }
  async function download(format: 'pdf' | 'json') {
    if (busy || !report) return;
    setBusy(true); setExporting(format); setExportError(''); setDownloadStatus('');
    const controller = new AbortController();
    exportController.current = controller;
    try {
      const response = await downloadResponse('/api/report/export', { method: 'POST', signal: controller.signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...requestBody(), format }) });
      const blob = await response.blob();
      if (controller.signal.aborted) return;
      const filename = /filename="(cv-analysis-[a-f0-9]{8}\.(?:pdf|json))"/.exec(response.headers.get('Content-Disposition') ?? '')?.[1] ?? `cv-analysis-${report.analysis_id.slice(0, 8)}.${format}`;
      setDownloadStatus(await saveReport(blob, filename));
    } catch (error) { if (!controller.signal.aborted) setExportError(requestMessage(error)); }
    finally { setBusy(false); setExporting(null); }
  }
  async function compare(nextDecisions = decisions) {
    if (busy) return;
    setBusy(true); setError(''); setExportError(''); setDownloadStatus('');
    try {
      const response = await checkedFetch('/api/compare', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(requestBody(nextDecisions)) });
      const body = parseReport(await response.json());
      setReport(body); setDecisions(nextDecisions);
    } catch (error) { setError(requestMessage(error)); }
    finally { setBusy(false); }
  }
  function decide(requirementId: string, evidenceId: string, decision: 'accept' | 'reject') {
    const next = decisions.filter(item => item.requirement_id !== requirementId || (decision === 'reject' && item.evidence_id !== evidenceId));
    void compare([...next, { requirement_id: requirementId, evidence_id: evidenceId, decision }]);
  }
  const pending = new Set(report?.possible_evidence.filter(item => item.decision === 'pending' && !report.matches.some(match => match.requirement_id === item.requirement_id)).map(item => item.requirement_id));
  return <section className="comparison-panel" aria-labelledby="comparison-title" aria-busy={busy}>
    <div className="section-heading"><div><span className="eyebrow">04 · CONNECT THE EVIDENCE</span><h2 id="comparison-title">How your resume fits this role</h2></div></div>
    <div className="card"><p className="muted">Compare the confirmed requirements with your reviewed text. Skill mentions describe evidence, not verified proficiency.</p>
      <details className="mapping-controls"><summary>Map an unfamiliar skill name (optional)</summary><p>Only map genuine aliases. You can instead change an unknown requirement to informational or excluded above.</p>{profile.job_requirements.filter(item => ['required_skill', 'preferred_skill'].includes(item.category)).map(item => <label key={item.id}>{item.name}<select aria-label={'Map ' + item.name} disabled={busy} value={mappings[item.id] ?? ''} onChange={event => { setMappings(previous => ({ ...previous, [item.id]: event.target.value })); setReport(null); setDecisions([]); setAiContext(null); setAiError(''); }}><option value="">Use detected canonical skill</option>{catalog.map(name => <option key={name} value={name}>{name}</option>)}</select></label>)}</details>
      <button className="analyze-button compare-button" disabled={busy} onClick={() => void compare()}>{busy ? <><LoaderCircle className="spin" size={18} />{aiBusy ? 'Analyzing with OpenAI…' : exporting ? 'Preparing report…' : 'Comparing evidence…'}</> : <>Compare with this role<ArrowRight size={18} /></>}</button>
      {error ? <div className="error" role="alert">{error}</div> : null}
    </div>
    {report ? <div className="comparison-report">
      <div className="card report-downloads"><div><h3>Save your report</h3><p>Download scores, reviewed evidence, and your improvement plan. JSON also includes the reviewed resume sections.</p></div><div className="download-buttons"><button type="button" disabled={busy} onClick={() => void download('pdf')}>{exporting === 'pdf' ? 'Preparing PDF...' : 'Download PDF'}</button><button type="button" disabled={busy} onClick={() => void download('json')}>{exporting === 'json' ? 'Preparing JSON...' : 'Download JSON'}</button></div>{exportError ? <div className="error" role="alert">{exportError}</div> : null}<p className="download-status" role="status" aria-live="polite">{downloadStatus}</p></div>
      <div className="match-summary card" role="status"><div><span className="eyebrow">ESTIMATED ATS ALIGNMENT</span><strong>{report.scores.overall === null ? 'Not scored' : report.scores.overall.toFixed(1) + '%'}</strong></div><p>{report.scores.overall === null ? 'No scored requirements apply. Add and review explicit skills or responsibilities.' : 'An application estimate based on documented evidence. This is not an employer ATS result or a hiring probability.'}<br />{report.informational_requirement_count} informational or excluded requirements · {pending.size} requirements with possible evidence</p></div>
      <div className="card ai-tools"><h3>AI and semantic resume analysis</h3><p>Get OpenAI advice grounded in your reviewed requirements and resume excerpts. Semantic proposals need your confirmation and do not automatically change the score.</p>{report.ai_analysis ? <><p role="status">AI analysis complete · {report.ai_analysis.model} · {report.ai_analysis.embedding_model}. {report.ai_analysis.discarded_rewrites} unsupported rewrites discarded. AI advice appears in your improvement plan and downloads.</p><button type="button" disabled={busy} onClick={() => { setAiContext(null); setReport(null); setDecisions([]); setAiError(''); setError(''); setDownloadStatus(''); }}>Clear AI analysis and evidence confirmations</button></> : <><label><input type="checkbox" checked={aiConsent} disabled={busy} onChange={event => setAiConsent(event.target.checked)} />Allow reviewed job wording and resume excerpts to be sent to OpenAI for this analysis. API charges may apply.</label><button type="button" disabled={busy || !aiConsent || !aiAvailable} onClick={() => void enhance()}>{aiBusy ? 'Analyzing…' : 'Generate AI advice and semantic proposals'}</button>{!aiAvailable ? <p>OpenAI is not configured on the backend. Set OPENAI_API_KEY and restart the API to enable this feature. Your local analysis remains available.</p> : null}</>}{aiError ? <div className="error" role="alert">{aiError}</div> : null}</div>
      <div className="score-grid">{Object.entries(report.scores.components).map(([key, value]) => <div className="card score-card" key={key}><h3>{componentNames[key]}</h3><strong>{value.score === null ? 'Not applicable' : value.score.toFixed(1) + '%'}</strong><p>{value.credited_weight} / {value.total_weight} requirement weight credited</p><p>{(100 * value.effective_weight).toFixed(1)}% of the overall score</p></div>)}</div>
      <div className="card requirement-report"><div className="card-title"><h3>Requirement evidence</h3></div><label htmlFor="report-filter">Show requirements</label><select id="report-filter" value={filter} onChange={event => setFilter(event.target.value)}><option value="all">All</option><option value="evidenced">Evidenced</option><option value="review">Needs review</option><option value="missing">Not evidenced</option></select>
        {report.requirements.filter(item => item.included_in_score).filter(item => filter === 'all' || (filter === 'evidenced' ? report.matches.some(m => m.requirement_id === item.id) : filter === 'review' ? pending.has(item.id) : report.requirements_not_evidenced.includes(item.id))).map(item => {
          const match = report.matches.find(m => m.requirement_id === item.id);
          const candidates = report.possible_evidence.filter(m => m.requirement_id === item.id);
          return <article className="evidence-row" key={item.id}><div><h4>{item.name}</h4><small>{categoryNames[item.category]}</small></div><span className={'outcome ' + (match ? 'positive' : 'missing')}>{match ? match.status + (match.method === 'user_confirmed' ? ' · user confirmed' : '') : pending.has(item.id) ? 'Needs review · no credit yet' : 'Not evidenced in this resume'}</span>
            <details><summary>Job wording</summary>{item.sources.map((source, index) => <blockquote key={index}>{source.text}</blockquote>)}</details>
            {match ? <div className="matched-excerpt"><small>{match.evidence.section} · {match.method}</small><blockquote>{match.evidence.text}</blockquote></div> : candidates.length ? <details><summary>Review possible resume evidence ({candidates.length})</summary>{candidates.map(candidate => <div className="possible-excerpt" key={candidate.evidence.id}><small>{candidate.evidence.section}</small><blockquote>{candidate.evidence.text}</blockquote><p>{candidate.reason}</p>{candidate.decision === 'pending' ? <div className="decision-buttons"><button disabled={busy} onClick={() => decide(item.id, candidate.evidence.id, 'accept')}>Confirm relevance</button><button disabled={busy} onClick={() => decide(item.id, candidate.evidence.id, 'reject')}>Reject</button></div> : <p>{candidate.decision === 'reject' ? 'Rejected · no credit' : 'Confirmed'}</p>}</div>)}</details> : <p className="muted">No eligible positive evidence was found. Learning and negated mentions earn no points.</p>}
          </article>;
        })}
      </div>
      <div className="profile-grid"><div className="card"><h3>Qualifications &amp; experience</h3>{report.qualifications.length ? report.qualifications.map(item => <article className="evidence-row" key={item.requirement_id}><h4>{report.requirements.find(r => r.id === item.requirement_id)?.name}</h4><span className="outcome">{item.status.replaceAll('_', ' ')}</span><p>{item.reason}</p>{item.evidence ? <blockquote>{item.evidence.text}</blockquote> : null}</article>) : <p className="muted">No explicit qualification requirements found.</p>}<p className="muted">These findings do not change your score.</p></div><div className="card"><h3>Readability checks</h3><p>{report.readability.status.replaceAll('_', ' ')}</p>{report.readability.issues.map((issue, index) => <p className="muted" key={index}>{issue}</p>)}<p className="muted">Readability does not contribute score points.</p></div></div>
      <ImprovementSuggestions key={report.analysis_id} report={report} />
      <div className="profile-warnings">{report.warnings.map(warning => <p key={warning}>{warning}</p>)}</div>
    </div> : null}
  </section>;
}
