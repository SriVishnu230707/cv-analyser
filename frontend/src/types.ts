export interface Requirement { id: string; category: string; name: string; weight: number; source: string }
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
