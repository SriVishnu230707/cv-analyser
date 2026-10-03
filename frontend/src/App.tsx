import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ArrowRight, ArrowUpRight, FileText, Leaf, LoaderCircle, ScanLine, Upload, X } from 'lucide-react';
import type { AnalysisReport } from './types';

async function request(url: string, options?: RequestInit) {
  const response = await fetch(url, { ...options, signal: AbortSignal.timeout(20000) });
  if (!response.ok) {
    let message = 'Cannot complete the request. Check that the API is running, then try again.';
    try { const body = await response.json(); if (typeof body.message === 'string') message = body.message; } catch {}
    throw new Error(message);
  }
  return response;
}
function Results({ report }: { report: AnalysisReport }) {
  const requirements = new Map(report.requirements.map(item => [item.id, item]));
  const names: Record<string, string> = { required_skills: 'Required skills', preferred_skills: 'Preferred skills', responsibilities: 'Responsibilities' };
  return <section className="results" aria-labelledby="results-title">
    <div className="section-heading"><h2 id="results-title">Example analysis</h2><span className="pill">Fixed sample report</span></div>
    <div className="score-panel"><div className="score-circle"><strong>{report.scores.overall ?? '—'}</strong><span>out of 100</span></div><div className="score-copy"><h3>Job match estimate</h3><p>This example uses the synthetic Python backend resume. It does not evaluate your uploaded document.</p></div><div className="breakdown">{Object.entries(report.scores.components).map(([name, component]) => <div key={name}><div className="bar-label"><span>{names[name]}</span><b>{component.score ?? 'N/A'}%</b></div><div className="bar"><span style={{ width: (component.score ?? 0) + '%' }} /></div><small>{Math.round(component.effective_weight * 100)}% of match score</small></div>)}</div></div>
    <div className="result-grid"><div className="card"><h3>Evidence found</h3>{report.matches.map(match => <details className="evidence" key={match.requirement_id}><summary><span>{requirements.get(match.requirement_id)?.name}</span><span className="evidence-status">{match.status}</span></summary><blockquote>{match.evidence.text}</blockquote><small>{match.evidence.section} · {match.method} match</small></details>)}</div><div className="card"><h3>Not evidenced</h3><div className="gap-list">{report.requirements_not_evidenced.map(id => <div key={id}><span className="gap-dot" /><span>{requirements.get(id)?.name}</span></div>)}</div><div className="qualification"><h4>Qualification review</h4>{report.qualifications.map(item => <p key={item.requirement_id}><strong>{requirements.get(item.requirement_id)?.name}</strong><br />{item.reason}</p>)}</div></div></div>
    <div className="card suggestion-card"><h3>Ways to strengthen the resume</h3>{report.suggestions.map((suggestion, index) => <article className="suggestion" key={index}><span className="suggestion-number">0{index + 1}</span><div><span className={'priority ' + suggestion.priority}>{suggestion.priority} priority</span><h4>{suggestion.rationale}</h4><p>{suggestion.action}</p>{suggestion.rewrite ? <blockquote>{suggestion.rewrite}</blockquote> : null}</div></article>)}</div>
    <p className="result-footnote">Readability: {report.readability.status.replaceAll('_', ' ')}. {report.warnings.join(' ')}</p>
  </section>;
}
export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const count = job.trim().length;
  const valid = file !== null && count >= 100 && count <= 20000;
  async function loadExample() {
    setBusy(true); setError(''); setReport(null); setNotice('');
    try {
      const [jobResponse, fileResponse] = await Promise.all([request('/api/demo/job'), request('/api/demo/resume')]);
      const [data, blob] = await Promise.all([jobResponse.json(), fileResponse.blob()]);
      setJob(data.job_description); setFile(new File([blob], 'sample-resume.pdf', { type: 'application/pdf' }));
      if (inputRef.current) inputRef.current.value = '';
      setNotice('Example resume and job description loaded. Ready to try the demo.');
    } catch (error) { setError(error instanceof Error ? error.message : 'Unable to load the example.'); }
    finally { setBusy(false); }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!file || !valid || busy) return;
    setBusy(true); setError(''); setNotice(''); setReport(null);
    try {
      const body = new FormData(); body.append('resume', file); body.append('job_description', job.trim());
      const response = await request('/api/analyze', { method: 'POST', body });
      setReport(await response.json()); setNotice('Sample report loaded. Your uploaded resume has not been analyzed.');
      requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth' }));
    } catch (error) { setError(error instanceof Error ? error.message : 'Unable to load the sample report.'); }
    finally { setBusy(false); }
  }
  return <><header className="topbar"><a className="brand" href="#"><span className="brand-mark"><Leaf size={22} /></span>cv<span className="brand-light">analyser</span><span className="brand-dot">.</span></a><span className="phase-badge">Phase 2 demo</span></header>
    <main><section className="hero"><div className="eyebrow">MAKE YOUR EXPERIENCE COUNT</div><h1>Your next opportunity.<br /><span>A stronger first impression.</span></h1><p>Connect your experience to what a role needs.<br />Find the evidence, spot the gaps, and make every word work harder.</p></section>
    <div className="demo-banner"><ScanLine size={19} /><p><strong>You’re exploring the Phase 2 demo.</strong> Every valid submission returns the same example report. Resume parsing and personalized analysis come in later phases.</p></div>
    <div className="workspace"><section className="input-card" aria-labelledby="form-title"><div className="section-heading"><h2 id="form-title">Resume meets opportunity</h2><span className="step-badge">01 / 02</span></div><form onSubmit={submit}>
    <div className="field-heading"><label htmlFor="resume">Your resume</label><span>PDF or DOCX</span></div><div className={'upload-area ' + (file ? 'has-file' : '')}><div className="upload-icon">{file ? <FileText size={25} /> : <Upload size={25} />}</div><strong>{file ? file.name : 'Bring your experience along'}</strong><p>{file ? (file.size / 1024).toFixed(1) + ' KB · Ready to upload' : 'Choose a resume from your device'}</p><label className="choose-file" htmlFor="resume">{file ? 'Choose another file' : 'Choose file'}<ArrowUpRight size={15} /></label><input ref={inputRef} id="resume" type="file" accept=".pdf,.docx" disabled={busy} aria-describedby="file-help" onChange={event => {
      const selected = event.target.files?.[0] ?? null; setError(''); setReport(null); setNotice('');
      if (selected && (!/\.(pdf|docx)$/i.test(selected.name) || !selected.size || selected.size > 5 * 1024 * 1024)) { setFile(null); event.target.value = ''; setError('Choose a non-empty PDF or DOCX file, up to 5 MiB.'); return; }
      setFile(selected);
    }} /><small id="file-help">Up to 5 MiB · Your file is not saved</small>{file ? <button className="remove-file" type="button" disabled={busy} aria-label="Remove resume" onClick={() => { setFile(null); setReport(null); setNotice(''); if (inputRef.current) inputRef.current.value = ''; }}><X size={16} /></button> : null}</div>
    <div className="field-heading job-heading"><label htmlFor="job">The role you have in mind</label><span>Job description</span></div><textarea id="job" value={job} maxLength={20000} disabled={busy} placeholder="Paste the job description here…" aria-describedby="job-help" onChange={event => { setJob(event.target.value); setReport(null); setNotice(''); }} /><div className="textarea-help" id="job-help"><span>Include at least 100 characters</span><span>{count.toLocaleString()} / 20,000</span></div>
    {error ? <div className="error" role="alert">{error}</div> : null}<p className="status-message" role="status">{notice}</p><button type="submit" className="analyze-button" disabled={!valid || busy}>{busy ? <><LoaderCircle className="spin" size={18} />Loading…</> : <>View sample analysis<ArrowRight size={18} /></>}</button><div className="form-bottom"><span>Temporary processing. No saved resume.</span><button type="button" className="text-button" disabled={busy} onClick={loadExample}>Load example<ArrowUpRight size={14} /></button></div></form></section>
    <aside className="guide"><div className="guide-top"><span className="eyebrow">LESS GUESSWORK. MORE CLARITY.</span><h2>A little perspective<br />goes a long way.</h2><p>A useful report connects each finding to real resume evidence.</p></div><div className="guide-item"><div><h3>Understand the match</h3><p>See required skills, preferred skills, and responsibility alignment.</p></div></div><div className="guide-item"><div><h3>Look beyond keywords</h3><p>Read the exact text behind each match.</p></div></div><div className="guide-note"><p>Your experience is more than a number. Use the score alongside the evidence.</p></div></aside></div><div ref={resultsRef}>{report ? <Results report={report} /> : null}</div><footer><span>cv analyser · Built around your experience</span><span>Scores are estimates, not hiring predictions.</span></footer></main></>;
}
