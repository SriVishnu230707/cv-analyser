import Ajv2020 from 'ajv/dist/2020';
import schema from '../../contracts/analysis-result-v1.1.schema.json';
import type { ComparisonReport } from './types';

const validate = new Ajv2020({ strict: false }).compile<ComparisonReport>(schema);

export function parseReport(value: unknown): ComparisonReport {
  if (!validate(value)) throw new Error('The server returned an invalid analysis report. Your previous report is still available. Please retry.');
  return value;
}

export function parseAIResponse(value: unknown, inputHash: string): { report: ComparisonReport; ai_context: string } {
  if (!value || typeof value !== 'object' || !('ai_context' in value) || typeof value.ai_context !== 'string' || !value.ai_context || value.ai_context.length > 200000 || !('report' in value)) {
    throw new Error('The server returned invalid AI analysis. Your local report is still available. Please retry.');
  }
  const report = parseReport(value.report);
  if (report.input_hash !== inputHash || !report.ai_analysis) throw new Error('The AI analysis does not match your current report. Please retry.');
  return { report, ai_context: value.ai_context };
}
