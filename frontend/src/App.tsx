import { useRef, useState } from 'react';
import type { FormEvent, ChangeEvent } from 'react';
import { ArrowRight, ArrowUpRight, Check, FileText, Leaf, LoaderCircle, LockKeyhole, ScanLine, Upload, X } from 'lucide-react';
import { ExtractionPreview } from './ExtractionPreview';
import { StructuredProfile } from './StructuredProfile';
import { ComparisonPanel } from './ComparisonPanel';
import type { ExtractionResult, PreparedResume, RequirementCategory } from './types';
import { checkedFetch, requestMessage } from './api';
import { SkillDictionary } from './SkillDictionary';

const MAX_BYTES = 5 * 1024 * 1024;
export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState('');
  const [error, setError] = useState('');
  const [previewError, setPreviewError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState<'example' | 'extract' | 'prepare' | 'review' | null>(null);
  const [extraction, setExtraction] = useState<ExtractionResult | null>(null);
  const [context, setContext] = useState<string | null>(null);
  const [text, setText] = useState('');
  const [reviewed, setReviewed] = useState(false);
  const [prepared, setPrepared] = useState<PreparedResume | null>(null);
  const [requirementEdits, setRequirementEdits] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const previewRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);
  const count = job.trim().length;
  function clearExtraction() {
    setContext(null);
    setExtraction(null); setText(''); setReviewed(false); setPrepared(null); setPreviewError('');
  }
  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setError(''); setNotice(''); clearExtraction();
    if (selected && (!/\.(pdf|docx)$/i.test(selected.name) || selected.size === 0 || selected.size > MAX_BYTES)) {
      setFile(null); event.target.value = '';
      setError('Choose a non-empty PDF or DOCX file, up to 5 MiB.'); return;
    }
    setFile(selected);
  }
  async function loadExample() {
    setBusy('example'); setError(''); setNotice(''); clearExtraction();
    try {
      const [jobResponse, fileResponse] = await Promise.all([checkedFetch('/api/demo/job'), checkedFetch('/api/demo/resume')]);
      const [jobData, blob] = await Promise.all([jobResponse.json(), fileResponse.blob()]);
      setJob(jobData.job_description);
      setFile(new File([blob], 'sample-resume.pdf', { type: 'application/pdf' }));
      if (inputRef.current) inputRef.current.value = '';
      setNotice('Example loaded. Extract the resume to review its actual text.');
    } catch (error) { setError(requestMessage(error)); }
    finally { setBusy(null); }
  }
  async function extract(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || busy) return;
    setBusy('extract'); setError(''); setNotice(''); clearExtraction();
    try {
      const form = new FormData(); form.append('resume', file);
      const response = await checkedFetch('/api/extract', { method: 'POST', body: form });
      const result: ExtractionResult = await response.json();
      setContext(response.headers.get('X-Extraction-Context'));
      setExtraction(result); setText(result.text);
      requestAnimationFrame(() => previewRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    } catch (error) { setError(requestMessage(error)); }
    finally { setBusy(null); }
  }
  async function prepare() {
    if (busy || !reviewed || count < 100 || count > 20000 || text.trim().length < 40) return;
    setBusy('prepare'); setPreviewError(''); setPrepared(null);
    try {
      const response = await checkedFetch('/api/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ resume_text: text, job_description: job }) });
      const result: PreparedResume = await response.json();
      setPrepared(result);
      setRequirementEdits(false);
      requestAnimationFrame(() => profileRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    } catch (error) { setPreviewError(requestMessage(error)); }
    finally { setBusy(null); }
  }
  async function reviewRequirements(corrections: { requirement_id: string; category: RequirementCategory }[]) {
    if (busy || !prepared) return;
    setBusy('review'); setPreviewError('');
    try {
      const response = await checkedFetch('/api/requirements/review', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ resume_text: prepared.resume_text, job_description: prepared.job_description, corrections }) });
      setPrepared(await response.json());
      setRequirementEdits(false);
    } catch (error) { setPreviewError(requestMessage(error)); }
    finally { setBusy(null); }
  }
  return <>
    <header className="topbar"><a className="brand" href="#"><span className="brand-mark"><Leaf size={22} /></span>cv<span className="brand-light">analyser</span><span className="brand-dot">.</span></a><div className="header-right"><span className="header-label">A clearer path to your next role</span><span className="phase-badge">Phase 8 · Broader matching</span></div></header>
    <main>
      <section className="hero"><div className="eyebrow"><span className="tiny-star">✦</span> MAKE YOUR EXPERIENCE COUNT</div><h1>Your next opportunity.<br /><span>A stronger first impression.</span></h1><p>Start with the words behind your experience.<br className="desktop-break" /> Extract your resume, check the details, and review the skills a role needs.</p><div className="hero-points"><span><Check size={15} /> PDF &amp; DOCX</span><span><Check size={15} /> Local English OCR</span><span><Check size={15} /> Editable text preview</span></div></section>
      <div className="demo-banner"><ScanLine size={19} /><p><strong>Your improvement plan is live.</strong> Review your text and job requirements, then compare evidence and get prioritized, factual suggestions.</p></div>
      <SkillDictionary />
      <div className="workspace">
        <section className="input-card" aria-labelledby="form-title"><div className="section-heading"><div><span className="eyebrow">START WITH THE BASICS</span><h2 id="form-title">Resume meets opportunity</h2></div><span className="step-badge">01 / 03</span></div>
          <form onSubmit={extract}>
            <div className="field-heading"><label htmlFor="resume"><span className="field-number">1</span>Your resume</label><span>PDF or DOCX</span></div>
            <div className={'upload-area ' + (file ? 'has-file' : '')}><div className="upload-icon">{file ? <FileText size={25} /> : <Upload size={25} />}</div><strong>{file ? file.name : 'Bring your experience along'}</strong><p>{file ? (file.size / 1024).toFixed(1) + ' KB · Ready to extract' : 'Choose a resume from your device'}</p><label className="choose-file" htmlFor="resume">{file ? 'Choose another file' : 'Choose file'}<ArrowUpRight size={15} /></label><input ref={inputRef} id="resume" type="file" accept=".pdf,.docx" onChange={selectFile} disabled={busy !== null} aria-describedby="file-help" /><small id="file-help">Up to 5 MiB · PDFs up to 10 pages · Your file is not saved</small>{file ? <button className="remove-file" type="button" aria-label="Remove resume" disabled={busy !== null} onClick={() => { setFile(null); clearExtraction(); setError(''); setNotice(''); if (inputRef.current) inputRef.current.value = ''; }}><X size={16} /></button> : null}</div>
            <div className="field-heading job-heading"><label htmlFor="job"><span className="field-number">2</span>The role you have in mind</label><span>Job description</span></div>
            <textarea id="job" value={job} onChange={event => { setJob(event.target.value); setPrepared(null); setPreviewError(''); setNotice(''); }} placeholder="Paste the job description here. You can also add it after reviewing the extracted resume…" disabled={busy !== null} maxLength={20000} aria-describedby="job-help" />
            <div className="textarea-help" id="job-help"><span>{count > 0 && count < 100 ? (100 - count) + ' more characters needed before preparation' : 'At least 100 characters to prepare for matching'}</span><span>{count.toLocaleString()} / 20,000</span></div>
            {error ? <div className="error" role="alert">{error}</div> : null}
            <p className="status-message" role="status" aria-live="polite">{notice}</p>
            <button className="analyze-button" type="submit" disabled={!file || busy !== null}>{busy === 'extract' ? <><LoaderCircle className="spin" size={18} />Extracting text…</> : <>{extraction ? 'Re-extract original file' : 'Extract resume text'}<ArrowRight size={18} /></>}</button>
            <div className="form-bottom"><span><LockKeyhole size={13} />Local processing. No saved resume.</span><button type="button" className="text-button" disabled={busy !== null} onClick={loadExample}>{busy === 'example' ? 'Loading example…' : 'Load example'}<ArrowUpRight size={14} /></button></div>
          </form>
        </section>
        <aside className="guide"><div className="guide-top"><span className="eyebrow">A RELIABLE FIRST STEP</span><h2>Your words.<br />Clearly understood.</h2><p>A good comparison starts with complete, readable resume text.</p></div><div className="guide-item"><span className="guide-icon"><ScanLine size={21} /></span><div><h3>Extract the real content</h3><p>Read PDF text and Word paragraphs and tables. Scanned PDFs use local English OCR when available.</p></div></div><div className="guide-item"><span className="guide-icon"><FileText size={21} /></span><div><h3>Check the reading order</h3><p>Columns, images, and layouts can affect extraction. Review every important section before continuing.</p></div></div><div className="guide-item"><span className="guide-icon"><Check size={21} /></span><div><h3>Correct and prepare</h3><p>Edit the text without uploading again, then extract skills and review job requirements with their source wording.</p></div></div><div className="guide-note"><span>✦</span><p>Encrypted or damaged files need a fresh, unlocked export. Use a clear PDF scan for the best OCR results.</p></div></aside>
      </div>
      <div ref={previewRef}>{extraction ? <ExtractionPreview extraction={extraction} text={text} reviewed={reviewed} prepared={prepared} busy={busy !== null} preparing={busy === 'prepare'} jobValid={count >= 100 && count <= 20000} error={previewError} onTextChange={value => { setText(value); setReviewed(false); setPrepared(null); setPreviewError(''); }} onReviewedChange={value => { setReviewed(value); setPrepared(null); }} onRestore={() => { setText(extraction.text); setReviewed(false); setPrepared(null); setPreviewError(''); }} onPrepare={prepare} /> : null}</div>
      <div ref={profileRef}>{prepared ? <StructuredProfile key={prepared.preparation_id} profile={prepared} disabled={busy !== null} error={previewError} onCategoryEdit={() => setRequirementEdits(true)} onReview={reviewRequirements} /> : null}</div>
      {prepared?.review_status === 'confirmed' && !requirementEdits ? <ComparisonPanel key={prepared.preparation_id} profile={prepared} context={context} /> : null}
      <footer><span>cv analyser · Built around your experience</span><span>Review your extracted text before continuing.</span></footer>
    </main>
  </>;
}
