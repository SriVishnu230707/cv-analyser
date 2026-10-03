import { useState } from 'react';
import { CheckCircle2, ListChecks, LoaderCircle, Tags } from 'lucide-react';
import type { PreparedResume, RequirementCategory } from './types';

export const categoryNames: Record<RequirementCategory, string> = {
  required_skill: 'Required skill', preferred_skill: 'Preferred skill', unclassified_skill: 'Skill — category unclear', responsibility: 'Responsibility', mandatory_qualification: 'Mandatory qualification', qualification: 'Qualification', experience_requirement: 'Experience requirement', other_requirement: 'Other requirement', excluded: 'Exclude from requirements',
};

interface Props {
  profile: PreparedResume;
  disabled: boolean;
  error: string;
  onReview: (corrections: { requirement_id: string; category: RequirementCategory }[]) => Promise<void>;
}

export function StructuredProfile({ profile, disabled, error, onReview }: Props) {
  const [categories, setCategories] = useState<Record<string, RequirementCategory>>({});
  const [saving, setSaving] = useState(false);
  const changed = Object.keys(categories).length > 0;
  const unresolved = profile.job_requirements.filter(item => (categories[item.id] ?? item.category) === 'unclassified_skill').length;
  const confirmed = profile.review_status === 'confirmed' && !changed;
  async function confirm() {
    setSaving(true);
    try { await onReview(profile.job_requirements.map(item => ({ requirement_id: item.id, category: categories[item.id] ?? item.category }))); }
    finally { setSaving(false); }
  }
  return <section className="structured-profile" aria-labelledby="profile-title">
    <div className="section-heading"><div><span className="eyebrow">03 / 03 · SEE WHAT THE WORDS SAY</span><h2 id="profile-title">Skills &amp; job requirements</h2></div><span className="pill">Dictionary v{profile.taxonomy_version}</span></div>
    <div className="profile-grid"><div className="card"><div className="card-title"><Tags size={19} /><h3>Resume skill evidence</h3><span className="count">{profile.resume_skills.length}</span></div><p className="muted">These are text mentions, not verified proficiency. Expand a skill to see where it appears.</p>{profile.resume_skills.length === 0 ? <p className="empty-profile">No dictionary skills found. Check the resume text and supported skill list.</p> : profile.resume_skills.map(skill => <details className="skill-evidence" key={skill.name}><summary><span>{skill.name}</span><span className="skill-levels">{[...new Set(skill.evidence.map(item => item.level))].join(' · ')}</span></summary>{skill.evidence.map((item, index) => <div className="skill-source" key={index}><div className="source-meta"><span>{item.section}</span><span className={'assertion ' + item.assertion}>{item.level}</span></div><blockquote>{item.text}</blockquote><small>Matched wording: “{item.matched_text}”</small></div>)}</details>)}</div>
      <div className="card"><div className="card-title"><ListChecks size={19} /><h3>Job requirements</h3><span className="count">{profile.job_requirements.length}</span></div><p className="muted">Check categories against the original wording. Unclear or conflicting classifications need your review.</p>{profile.job_requirements.length === 0 ? <p className="empty-profile">No assessable requirements found. Add explicit job requirements above and extract again.</p> : profile.job_requirements.map(item => <article className={'job-requirement ' + (item.needs_review ? 'needs-review' : '')} key={item.id}><h4>{item.name}</h4><label htmlFor={'category-' + item.id}>Requirement category</label><select id={'category-' + item.id} value={categories[item.id] ?? item.category} disabled={disabled || saving} onChange={event => setCategories(previous => ({ ...previous, [item.id]: event.target.value as RequirementCategory }))}>{Object.entries(categoryNames).map(([category, name]) => <option key={category} value={category}>{name}</option>)}</select>{item.needs_review && !categories[item.id] ? <p className="review-reason">{item.review_reason}</p> : null}<details className="requirement-source"><summary>Source wording · {item.sources.length} {item.sources.length === 1 ? 'excerpt' : 'excerpts'}</summary>{item.sources.map((source, index) => <div key={index}><blockquote>{source.text}</blockquote><small>Job description · line {source.line_number}</small></div>)}<small>Classification: {item.classification_method}</small></details></article>)}
        {profile.excluded_job_mentions.length > 0 ? <details className="excluded-mentions"><summary>Explicitly excluded mentions ({profile.excluded_job_mentions.length})</summary>{profile.excluded_job_mentions.map((item, index) => <div key={index}><strong>{item.name}</strong><p>{item.reason}</p><blockquote>{item.source}</blockquote></div>)}</details> : null}
        {unresolved > 0 ? <p className="preview-hint">Choose a category for {unresolved} unclear {unresolved === 1 ? 'skill' : 'skills'} before confirming.</p> : null}
        {error ? <div className="error" role="alert">{error}</div> : null}
        <button type="button" className="analyze-button" disabled={disabled || saving || unresolved > 0 || profile.job_requirements.length === 0 || confirmed} onClick={confirm}>{saving ? <><LoaderCircle className="spin" size={18} />Saving review…</> : confirmed ? <><CheckCircle2 size={18} />Requirements confirmed</> : 'Confirm requirement categories'}</button>
        {confirmed ? <p className="confirmation-message" role="status">Your reviewed requirements are ready for Phase 5 matching. No match score has been calculated.</p> : null}
      </div></div><div className="profile-warnings">{profile.warnings.map((warning, index) => <p key={index}>{warning}</p>)}</div>
  </section>;
}
