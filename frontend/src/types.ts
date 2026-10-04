export interface Requirement { id: string; category: string; name: string; weight: number; source: string }
export interface ResumeSection { name: string; text: string }
export interface ExtractionResult {
  status: 'extracted'; file_type: 'pdf' | 'docx'; text: string; sections: ResumeSection[];
  pages: { number: number | null; text: string; method: 'text' | 'ocr' }[];
  page_count: number | null; ocr_used: boolean;
  readability: { status: 'readable' | 'needs_review'; issues: string[] }; warnings: string[];
}
export interface PreparedResume {
  status: 'ready_for_matching'; preparation_id: string; resume_text: string;
  resume_sections: ResumeSection[]; job_description: string; analysis_available: false; warnings: string[];
  taxonomy_version: string; resume_skills: ResumeSkill[]; job_requirements: JobRequirement[];
  excluded_job_mentions: { name: string; source: string; reason: string }[];
  review_status: 'needs_review' | 'not_confirmed' | 'confirmed'; pending_review_count: number;
}
export type RequirementCategory = 'required_skill' | 'preferred_skill' | 'unclassified_skill' | 'responsibility' | 'mandatory_qualification' | 'qualification' | 'experience_requirement' | 'other_requirement' | 'excluded';
export interface ResumeSkill {
  name: string;
  evidence: { text: string; section: string; matched_text: string; start: number; end: number; assertion: 'positive' | 'negated' | 'learning'; level: 'listed' | 'demonstrated' | 'mentioned' | 'negated' | 'learning' }[];
}
export interface JobRequirement {
  id: string; name: string; category: RequirementCategory; source: string;
  sources: { text: string; line_number: number }[]; classification_method: string;
  needs_review: boolean; review_reason: string; weight: number;
}
export interface AnalysisReport {
  schema_version: string;
  analysis_id: string;
  status: 'complete' | 'insufficient_requirements' | 'extraction_failed';
  requirements: Requirement[];
  matches: { requirement_id: string; status: 'listed' | 'demonstrated' | 'possible'; method: string; evidence: { text: string; section: string } }[];
  requirements_not_evidenced: string[];
  qualifications: { requirement_id: string; status: string; reason: string }[];
  scores: { overall: number | null; components: Record<string, { score: number | null; base_weight: number; effective_weight: number }> };
  readability: { status: string; issues: string[] };
  suggestions: { priority: string; requirement_ids: string[]; rationale: string; action: string; rewrite: string | null }[];
  warnings: string[];
}

export interface EvidenceExcerpt { id: string; text: string; section: string; section_index: number; start: number; end: number }
export interface EvidenceDecision { requirement_id: string; evidence_id: string; decision: 'accept' | 'reject' }
export interface ComparisonReport {
  ats_assessment?: { score: number | null; label: string; method: string; readability_status: string; disclaimer: string };
  ai_analysis?: { generation_id: string; provider: string; model: string; embedding_model: string; discarded_rewrites: number };
  schema_version: '1.1.0'; analysis_id: string; input_hash: string; status: 'complete' | 'insufficient_requirements';
  scoring_policy_version: string; taxonomy_version: string; rule_version: string;
  requirements: (JobRequirement & { canonical_skill: string | null; included_in_score: boolean })[];
  matches: { requirement_id: string; status: 'listed' | 'demonstrated'; method: string; evidence: EvidenceExcerpt }[];
  possible_evidence: { requirement_id: string; evidence: EvidenceExcerpt; reason: string; decision: 'pending' | 'accept' | 'reject' }[];
  requirements_not_evidenced: string[];
  qualifications: { requirement_id: string; status: 'met' | 'not_evidenced' | 'uncertain'; evidence: EvidenceExcerpt | null; reason: string }[];
  scores: { overall: number | null; components: Record<string, { score: number | null; base_weight: number; effective_weight: number; credited_weight: number; total_weight: number }> };
  readability: { status: string; issues: string[] }; informational_requirement_count: number; warnings: string[];
  suggestions: { id: string; priority: 'high' | 'medium' | 'low'; kind: string; requirement_ids: string[]; rationale: string; action: string; rewrite: string | null; evidence: EvidenceExcerpt | null }[];
}
