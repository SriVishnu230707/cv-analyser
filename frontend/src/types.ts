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
